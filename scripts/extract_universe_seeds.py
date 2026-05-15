"""
Extract instrument seeds from a FINFOX CSV export.

Reads IN_INSTRUMENTS_COMPLETE.csv, keeps only identifiers (isin, valor_nr,
ticker, name, instrument_type), deduplicates on ISIN, maps FINFOX class to
OpenWealth FinancialInstrumentType, and writes data/universe/seeds.parquet.

Run this once per new FINFOX data export. The seeds file is the input for
ingest_universe.py which fetches master and market data from the internet.

Usage:
    python scripts/extract_universe_seeds.py [--csv PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd

from universe.schemas import FINFOX_TO_OW, InstrumentSeed
from universe.store import ParquetUniverseStore

log = logging.getLogger("extract_seeds")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_finfox_csv(path: str) -> pd.DataFrame:
    """Parse semicolon-delimited FINFOX CSV with leading comment/section lines."""
    headers: list[str] = []
    rows: list[dict] = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n\r")
            if line.startswith("#") or line.startswith("IN_"):
                continue
            parts = line.split(";")
            if not headers:
                headers = parts
                continue
            if len(parts) >= len(headers) // 2:  # skip garbage lines
                rows.append(dict(zip(headers, parts)))
    return pd.DataFrame(rows)


def extract_seeds(df: pd.DataFrame) -> list[InstrumentSeed]:
    # Drop rows whose FINFOX class doesn't map to an OpenWealth type
    df = df[df["class"].isin(FINFOX_TO_OW)].copy()

    # Require a valid 12-character ISIN
    df = df[df["isin"].str.len() == 12]

    # Deduplicate: if same ISIN appears in multiple classes, prefer equity > bond > fund > other
    priority = {
        "equity": 0, "simpleBond": 1, "floater": 1, "convertibleBond": 1, "moneyMarket": 1,
        "fund": 2, "commodity": 3, "certificate": 3, "highlyStructuredProduct": 4,
        "callOption": 5, "putOption": 5, "future": 5, "other": 6,
    }
    df["_priority"] = df["class"].map(priority).fillna(99)
    df = df.sort_values("_priority").drop_duplicates(subset=["isin"], keep="first")
    df = df.drop(columns=["_priority"])

    seeds: list[InstrumentSeed] = []
    for _, row in df.iterrows():
        name = (row.get("name@de") or "").replace("\xa0", " ").strip()
        ticker = (row.get("tickerSymbol") or "").strip()
        currency = (row.get("nominalCurrency") or "").strip()
        isin = row["isin"].strip()
        valor = (row.get("valorenNr") or "").strip()
        ow_type = FINFOX_TO_OW[row["class"]]

        seeds.append(InstrumentSeed(
            isin=isin,
            valor_nr=valor,
            instrument_type=ow_type,
            name=name,
            ticker=ticker,
            nominal_currency=currency,
        ))

    return seeds


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract universe seeds from FINFOX CSV")
    parser.add_argument(
        "--csv",
        default="/Users/danielwirth/PycharmProjects/financial-advisory-project/data/IN_INSTRUMENTS_COMPLETE.csv",
        help="Path to IN_INSTRUMENTS_COMPLETE.csv",
    )
    parser.add_argument("--out", default="data/universe", help="Output directory")
    args = parser.parse_args()

    log.info("Parsing %s", args.csv)
    df = parse_finfox_csv(args.csv)
    log.info("Raw rows: %d, classes: %s", len(df), dict(df["class"].value_counts()))

    seeds = extract_seeds(df)

    from collections import Counter
    type_counts = Counter(s.instrument_type for s in seeds)
    log.info("Extracted %d unique seeds:", len(seeds))
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        log.info("  %-30s %d", t, c)

    store = ParquetUniverseStore(args.out)
    store.save_seeds(seeds)
    log.info("Written → %s/seeds.parquet", args.out)


if __name__ == "__main__":
    main()
