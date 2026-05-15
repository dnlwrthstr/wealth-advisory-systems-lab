"""Silver-tier accessors over the parquet universe store.

The bronze layer (FINFOX CSV → per-class parquet) is materialised by
`scripts/extract_universe_seeds.py` and `scripts/ingest_universe.py`. The
gold builders read seeds + masters from `data/universe/*.parquet` and
use them as the baseline that external sources (yfinance / FIRDS /
GLEIF) then enrich on top of.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

log = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data/universe")


# ISIN country (first 2 chars) → Yahoo ticker suffix. Used when the FINFOX
# ticker is bare (e.g. "ADS" for adidas — Yahoo wants "ADS.DE"). US tickers
# carry no suffix on Yahoo, so the empty-string default is correct.
ISIN_COUNTRY_TO_YAHOO_SUFFIX = {
    "US": "", "CA": ".TO",
    "GB": ".L",
    "DE": ".DE", "CH": ".SW", "FR": ".PA",
    "NL": ".AS", "BE": ".BR", "IT": ".MI",
    "ES": ".MC", "AT": ".VI", "FI": ".HE",
    "SE": ".ST", "DK": ".CO", "NO": ".OL",
    "PT": ".LS", "GR": ".AT", "IE": ".IR",
    "AU": ".AX", "NZ": ".NZ",
    "JP": ".T", "HK": ".HK", "SG": ".SI",
    "KR": ".KS", "TW": ".TW",
    "BR": ".SA", "MX": ".MX", "AR": ".BA",
}


def parquet_dir(data_dir: Path | str | None = None) -> Path:
    return Path(data_dir) if data_dir else DEFAULT_DATA_DIR


def _require(path: Path) -> Path:
    if not path.exists():
        raise SystemExit(
            f"Parquet file missing: {path}\n"
            "Run scripts/extract_universe_seeds.py and scripts/ingest_universe.py "
            "to materialise the silver tier first."
        )
    return path


def load_seeds(
    data_dir: Path | str | None = None,
    instrument_type: Optional[str] = None,
) -> pd.DataFrame:
    """Return seeds.parquet, optionally filtered by instrument_type."""
    df = pd.read_parquet(_require(parquet_dir(data_dir) / "seeds.parquet"))
    if instrument_type:
        df = df[df["instrument_type"] == instrument_type]
    return df.reset_index(drop=True)


def load_equity_master(data_dir: Path | str | None = None) -> pd.DataFrame:
    """Equity master rows from equity.parquet, indexed by ISIN."""
    return pd.read_parquet(_require(parquet_dir(data_dir) / "equity.parquet"))


def load_bond_master(data_dir: Path | str | None = None) -> pd.DataFrame:
    """Bond master rows from bond.parquet, indexed by ISIN."""
    return pd.read_parquet(_require(parquet_dir(data_dir) / "bond.parquet"))


def iter_equity_seeds(
    data_dir: Path | str | None = None,
) -> Iterator[dict]:
    """Yield merged seed+master records for equities.

    The seed file is the identifier baseline (ISIN, valor, ticker, name,
    currency). The master file overlays sector, country, exchange, esg.
    The merge is a left join on ISIN; rows present only in seeds yield
    the seed defaults.
    """
    seeds = load_seeds(data_dir, instrument_type="equity")
    try:
        master = load_equity_master(data_dir)
    except SystemExit:
        master = pd.DataFrame()
    if not master.empty:
        master = master.drop(columns=["instrument_type"], errors="ignore")
        merged = seeds.merge(
            master,
            on="isin",
            how="left",
            suffixes=("", "_m"),
        )
        # Prefer master values for the columns it covers; seeds otherwise.
        for col in ("name", "ticker", "nominal_currency"):
            mcol = f"{col}_m"
            if mcol in merged.columns:
                merged[col] = merged[mcol].fillna(merged[col])
                merged = merged.drop(columns=[mcol])
    else:
        merged = seeds.copy()

    for row in merged.to_dict("records"):
        yield {k: (v if v == v else None) for k, v in row.items()}  # NaN → None


def yahoo_ticker_for(isin: str, finfox_ticker: str) -> str:
    """Translate a FINFOX bare ticker into Yahoo's symbol convention by
    using the ISIN country code to attach the right venue suffix.
    """
    if not finfox_ticker:
        return ""
    # If the ticker already carries a venue suffix (".DE", ".L", …), trust it.
    if "." in finfox_ticker:
        return finfox_ticker
    country = (isin or "")[:2].upper()
    suffix = ISIN_COUNTRY_TO_YAHOO_SUFFIX.get(country)
    # Unknown country: pass through bare. yfinance will 404 → caller drops.
    if suffix is None:
        return finfox_ticker
    return finfox_ticker + suffix
