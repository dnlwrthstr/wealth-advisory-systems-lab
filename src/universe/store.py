"""Parquet-backed store for the instrument universe.

Files:
  seeds.parquet        — identifiers (isin, valor_nr, ticker, name, instrument_type)
  equity.parquet       — EquityMaster records
  bond.parquet         — BondMaster records (simpleBond, floater, convertibleBond, moneyMarket)
  market_data.parquet  — MarketSnapshot records, keyed by (isin, as_of)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .schemas import BondMaster, EquityMaster, InstrumentSeed, MarketSnapshot

_EQUITY_TYPES = {"equity"}
_BOND_TYPES = {"simple_bond", "floater", "convertible_bond", "money_market"}


class ParquetUniverseStore:
    def __init__(self, data_dir: str | Path = "data/universe"):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._seeds: pd.DataFrame = self._load("seeds.parquet")
        self._equity: pd.DataFrame = self._load("equity.parquet")
        self._bond: pd.DataFrame = self._load("bond.parquet")
        self._market: pd.DataFrame = self._load("market_data.parquet")

    def _load(self, filename: str) -> pd.DataFrame:
        path = self._dir / filename
        return pd.read_parquet(path) if path.exists() else pd.DataFrame()

    def _path(self, filename: str) -> Path:
        return self._dir / filename

    # ── Seeds ──────────────────────────────────────────────────────────────

    def save_seeds(self, records: list[InstrumentSeed]) -> None:
        df = pd.DataFrame([r.__dict__ for r in records])
        df.to_parquet(self._path("seeds.parquet"), index=False)
        self._seeds = df

    def list_seeds(self, instrument_type: str | None = None) -> list[InstrumentSeed]:
        df = self._seeds
        if df.empty:
            return []
        if instrument_type:
            df = df[df["instrument_type"] == instrument_type]
        return [InstrumentSeed(**r) for r in df.to_dict("records")]

    # ── Equity master ──────────────────────────────────────────────────────

    def save_equities(self, records: list[EquityMaster]) -> None:
        df = pd.DataFrame([r.__dict__ for r in records])
        df.to_parquet(self._path("equity.parquet"), index=False)
        self._equity = df

    def get_equity(self, isin: str) -> Optional[EquityMaster]:
        if self._equity.empty:
            return None
        row = self._equity[self._equity["isin"] == isin]
        return EquityMaster(**row.iloc[0].to_dict()) if not row.empty else None

    def search_equities(
        self, q: str = "", sector: str = "", country: str = "", limit: int = 50
    ) -> list[EquityMaster]:
        df = self._equity
        if df.empty:
            return []
        if q:
            ql = q.lower()
            mask = (
                df["name"].str.lower().str.contains(ql, na=False)
                | df["ticker"].str.lower().str.contains(ql, na=False)
                | df["isin"].str.lower().str.contains(ql, na=False)
                | df["issuer_name"].str.lower().str.contains(ql, na=False)
            )
            df = df[mask]
        if sector:
            df = df[df["sector"].str.lower() == sector.lower()]
        if country:
            df = df[df["country"].str.upper() == country.upper()]
        return [EquityMaster(**r) for r in df.head(limit).to_dict("records")]

    # ── Bond master ────────────────────────────────────────────────────────

    def save_bonds(self, records: list[BondMaster]) -> None:
        df = pd.DataFrame([r.__dict__ for r in records])
        df.to_parquet(self._path("bond.parquet"), index=False)
        self._bond = df

    def get_bond(self, isin: str) -> Optional[BondMaster]:
        if self._bond.empty:
            return None
        row = self._bond[self._bond["isin"] == isin]
        return BondMaster(**row.iloc[0].to_dict()) if not row.empty else None

    def search_bonds(
        self, q: str = "", rating: str = "", currency: str = "",
        instrument_type: str = "", limit: int = 50
    ) -> list[BondMaster]:
        df = self._bond
        if df.empty:
            return []
        if q:
            ql = q.lower()
            mask = (
                df["name"].str.lower().str.contains(ql, na=False)
                | df["isin"].str.lower().str.contains(ql, na=False)
                | df["issuer_name"].str.lower().str.contains(ql, na=False)
            )
            df = df[mask]
        if rating:
            df = df[df["rating"] == rating]
        if currency:
            df = df[df["nominal_currency"].str.upper() == currency.upper()]
        if instrument_type:
            df = df[df["instrument_type"] == instrument_type]
        return [BondMaster(**r) for r in df.head(limit).to_dict("records")]

    # ── Market snapshots ───────────────────────────────────────────────────

    def save_snapshots(self, records: list[MarketSnapshot]) -> None:
        new_df = pd.DataFrame([r.__dict__ for r in records])
        if not self._market.empty:
            # Upsert: replace existing (isin, as_of) pairs, append new ones
            combined = pd.concat([self._market, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["isin", "as_of"], keep="last")
            self._market = combined
        else:
            self._market = new_df
        self._market.to_parquet(self._path("market_data.parquet"), index=False)

    def get_latest_snapshot(self, isin: str) -> Optional[MarketSnapshot]:
        if self._market.empty:
            return None
        rows = self._market[self._market["isin"] == isin]
        if rows.empty:
            return None
        latest = rows.sort_values("as_of", ascending=False).iloc[0]
        return MarketSnapshot(**latest.to_dict())

    def get_snapshots(self, isin: str) -> list[MarketSnapshot]:
        if self._market.empty:
            return []
        rows = self._market[self._market["isin"] == isin].sort_values("as_of", ascending=False)
        return [MarketSnapshot(**r) for r in rows.to_dict("records")]

    # ── Snapshot ───────────────────────────────────────────────────────────

    def universe_snapshot(self) -> dict:
        summary = {}
        for label, df in [("seeds", self._seeds), ("equity", self._equity),
                           ("bond", self._bond), ("market_data", self._market)]:
            if df.empty:
                summary[label] = {"count": 0}
                continue
            info: dict = {"count": len(df)}
            if "instrument_type" in df.columns:
                info["by_type"] = df["instrument_type"].value_counts().to_dict()
            if "nominal_currency" in df.columns:
                info["by_currency"] = df["nominal_currency"].value_counts().head(8).to_dict()
            if label == "equity":
                if "sector" in df.columns:
                    info["by_sector"] = df["sector"].value_counts().head(10).to_dict()
                if "country" in df.columns:
                    info["by_country"] = df["country"].value_counts().head(10).to_dict()
            if label == "bond" and "rating" in df.columns:
                info["by_rating"] = df["rating"].value_counts().head(10).to_dict()
            summary[label] = info
        return summary
