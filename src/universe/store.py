"""Parquet-backed store for equity and bond golden records."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .schemas import BondRecord, EquityRecord

EQUITY_FILE = "equity.parquet"
BOND_FILE = "simpleBond.parquet"


class ParquetUniverseStore:
    def __init__(self, data_dir: str | Path = "data/universe"):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._equity: pd.DataFrame = self._load(EQUITY_FILE)
        self._bond: pd.DataFrame = self._load(BOND_FILE)

    def _load(self, filename: str) -> pd.DataFrame:
        path = self._dir / filename
        if path.exists():
            return pd.read_parquet(path)
        return pd.DataFrame()

    # ── Write ──────────────────────────────────────────────────────────────

    def save_equities(self, records: list[EquityRecord]) -> None:
        df = pd.DataFrame([r.__dict__ for r in records])
        df.to_parquet(self._dir / EQUITY_FILE, index=False)
        self._equity = df

    def save_bonds(self, records: list[BondRecord]) -> None:
        df = pd.DataFrame([r.__dict__ for r in records])
        df.to_parquet(self._dir / BOND_FILE, index=False)
        self._bond = df

    # ── Read ───────────────────────────────────────────────────────────────

    def get_equity(self, isin: str) -> Optional[EquityRecord]:
        if self._equity.empty:
            return None
        row = self._equity[self._equity["isin"] == isin]
        if row.empty:
            return None
        return EquityRecord(**row.iloc[0].to_dict())

    def get_bond(self, isin: str) -> Optional[BondRecord]:
        if self._bond.empty:
            return None
        row = self._bond[self._bond["isin"] == isin]
        if row.empty:
            return None
        return BondRecord(**row.iloc[0].to_dict())

    def search_equities(self, q: str = "", sector: str = "", country: str = "", limit: int = 50) -> list[EquityRecord]:
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
        return [EquityRecord(**r) for r in df.head(limit).to_dict("records")]

    def search_bonds(self, q: str = "", rating: str = "", currency: str = "", limit: int = 50) -> list[BondRecord]:
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
        return [BondRecord(**r) for r in df.head(limit).to_dict("records")]

    def snapshot(self) -> dict:
        result = {}
        for label, df in [("equity", self._equity), ("simpleBond", self._bond)]:
            if df.empty:
                result[label] = {"count": 0}
                continue
            info: dict = {"count": len(df)}
            if "nominal_currency" in df.columns:
                info["by_currency"] = df["nominal_currency"].value_counts().head(10).to_dict()
            if label == "equity" and "sector" in df.columns:
                info["by_sector"] = df["sector"].value_counts().head(10).to_dict()
            if label == "equity" and "country" in df.columns:
                info["by_country"] = df["country"].value_counts().head(10).to_dict()
            if label == "simpleBond" and "rating" in df.columns:
                info["by_rating"] = df["rating"].value_counts().head(10).to_dict()
            result[label] = info
        return result
