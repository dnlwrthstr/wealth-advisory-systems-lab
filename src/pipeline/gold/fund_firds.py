"""Fetch UCITS funds from ESMA FIRDS for a curated umbrella LEI list and
emit FundGolden NDJSON.

Per umbrella LEI: query FIRDS Solr, filter to CFI category C (funds),
dedupe by ISIN, build a validated `FundGolden` pydantic instance per
surviving doc, write NDJSON. Static fields (ISIN, CFI, sub-type derived
from CFI, domicile, legal framework) populate well. NAV / AUM / TER /
returns / holdings need NAV feeds and KIID parsing — left blank here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import yaml
from pydantic import ValidationError

from universe.models import (
    Country,
    Currency,
    FinancialInstrumentIdentification,
    FundGolden,
    GoldenRecordMeta,
    LegalEntityIdentifier,
    ListingSnapshot,
    OrganisationSnapshot,
    SourceAttribution,
    SourceFingerprint,
    UmbrellaSnapshot,
)

from ._firds import iter_issuer_records

log = logging.getLogger("fund_firds")

SCHEMA_VERSION = "0.1.0"

FIRDS_FL = [
    "isin", "lei",
    "gnr_full_name", "gnr_short_name", "gnr_cfi_code",
    "gnr_notional_curr_code",
    "mic", "rca_mic", "upcoming_rca",
    "mrkt_trdng_start_date", "status", "valid_from_date",
]

CFI_SUBTYPE_TO_FUND_SUBTYPE: Dict[str, str] = {
    "E": "etf",
    "O": "openEndedMutualFund",
    "C": "closeEndedFund",
    "I": "openEndedMutualFund",
    "R": "realEstateFund",
    "S": "structuredFund",
    "U": "hedgeFund",
}

CFI_DIVIDEND_POLICY: Dict[str, str] = {
    "I": "DISTRIBUTING",
    "G": "ACCUMULATING",
    "M": "ACCUMULATING",
}

CFI_EXPOSURE: Dict[str, str] = {
    "E": "equity", "B": "fixedIncome", "M": "mixed_balanced",
    "C": "moneyMarket", "R": "realEstate", "T": "commodity",
    "F": "alternative", "D": "alternative", "H": "alternative", "S": "alternative",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def derive_fund_sub_type(cfi: Optional[str]) -> str:
    cfi = (cfi or "").upper().ljust(6, "X")
    return CFI_SUBTYPE_TO_FUND_SUBTYPE.get(cfi[1], "other")


def derive_dividend_policy(cfi: Optional[str]) -> Optional[str]:
    cfi = (cfi or "").upper().ljust(6, "X")
    return CFI_DIVIDEND_POLICY.get(cfi[3])


def derive_primary_exposure(cfi: Optional[str]) -> Optional[str]:
    cfi = (cfi or "").upper().ljust(6, "X")
    return CFI_EXPOSURE.get(cfi[4])


def _iso_date(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v)
    return s.split("T", 1)[0] if "T" in s else s


def _lifecycle_status(status: Optional[str]) -> str:
    s = (status or "").upper()
    if s == "TERM":
        return "liquidated"
    if s == "CANC":
        return "inactive"
    return "active"


def _fingerprint(doc: Dict[str, Any]) -> str:
    payload = json.dumps(doc, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_issuers(path: Optional[Path]) -> List[Dict[str, Any]]:
    if path is None:
        text = files("pipeline.gold.data").joinpath("fund_umbrellas.yml").read_text(encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    issuers = data.get("issuers") or []
    if not issuers:
        raise SystemExit("Empty umbrella file.")
    for entry in issuers:
        if not entry.get("lei") or not entry.get("umbrellaName"):
            raise SystemExit(f"umbrella missing lei/umbrellaName: {entry}")
        entry.setdefault("managementCompany", entry["umbrellaName"])
        entry.setdefault("legalFramework", "UCITS")
        entry.setdefault("legalStructure", "Plc")
        entry.setdefault("country", "IE")
    return issuers


def _record_quality(doc: Dict[str, Any]) -> Tuple[int, int]:
    status = (doc.get("status") or "").upper()
    status_rank = {"UNCH": 3, "NEWT": 3, "TERM": 1, "CANC": 0}.get(status, 2)
    field_rank = sum(1 for v in doc.values() if v not in (None, ""))
    return status_rank, field_rank


def dedupe_by_isin(records: Iterator[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for doc in records:
        cfi = (doc.get("gnr_cfi_code") or "").upper()
        if not cfi.startswith("C"):
            continue
        isin = doc.get("isin")
        if not isin:
            continue
        current = best.get(isin)
        if current is None or _record_quality(doc) > _record_quality(current):
            best[isin] = doc
    return list(best.values())


# ---------------------------------------------------------------------------
# FIRDS doc → FundGolden
# ---------------------------------------------------------------------------

def firds_to_golden(
    doc: Dict[str, Any],
    issuer: Dict[str, Any],
    run_id: str,
    now: datetime,
) -> Optional[FundGolden]:
    now_iso = now.isoformat()
    isin = doc["isin"]
    cfi = doc.get("gnr_cfi_code")
    currency_code = doc.get("gnr_notional_curr_code")
    if not currency_code:
        return None  # FundGolden requires currencyOfDenomination

    fund_sub_type = derive_fund_sub_type(cfi)
    dividend_policy = derive_dividend_policy(cfi)
    primary_exposure = derive_primary_exposure(cfi)
    first_trading_date = _iso_date(doc.get("mrkt_trdng_start_date"))
    lifecycle = _lifecycle_status(doc.get("status"))

    asset_class_label = "Fund"
    asset_class_id = "AC-FUND"
    if primary_exposure == "equity":
        asset_class_label, asset_class_id = "Fund / Equity", "AC-FUND-EQ"
    elif primary_exposure == "fixedIncome":
        asset_class_label, asset_class_id = "Fund / Fixed Income", "AC-FUND-FI"
    elif primary_exposure == "mixed_balanced":
        asset_class_label, asset_class_id = "Fund / Multi-Asset", "AC-FUND-MA"
    if fund_sub_type == "etf":
        asset_class_label += " ETF"
        asset_class_id += "-ETF"

    currency = Currency(currency_code)
    country = Country(issuer["country"]) if issuer.get("country") else None

    primary_listing = ListingSnapshot(
        mic=doc.get("mic") or "XOFF",
        venueCountry=Country(doc["upcoming_rca"]) if doc.get("upcoming_rca") else None,
        listingCurrency=currency,
        firstTradingDate=first_trading_date,
        status="active" if lifecycle == "active" else "delisted",
        isPrimary=True,
    )

    identifier_list = [FinancialInstrumentIdentification(identifier=isin, type="isin")]

    umbrella = UmbrellaSnapshot(
        umbrellaId=f"UMB-{issuer['lei']}",
        legalName=issuer["umbrellaName"],
        lei=LegalEntityIdentifier(issuer["lei"]),
        domicileCountry=country,
        legalStructure=issuer.get("legalStructure"),
    )

    management_company = OrganisationSnapshot(
        organisationId=f"MGT-{issuer['lei']}",
        legalName=issuer["managementCompany"],
        lei=LegalEntityIdentifier(issuer["lei"]),
        organisationType="fund_company",
        domicileCountry=country,
        headquartersCountry=country,
    )

    meta = GoldenRecordMeta(
        schemaVersion=SCHEMA_VERSION,
        goldenAsOf=now_iso,
        ingestionRunId=run_id,
        sourceOfTruth=[
            SourceAttribution(fieldGroup="identifiers", source="esma-firds"),
            SourceAttribution(fieldGroup="classification", source="esma-firds + cfi-derived"),
            SourceAttribution(fieldGroup="umbrella", source="curated-issuers.yml"),
            SourceAttribution(fieldGroup="primaryListing", source="esma-firds"),
        ],
        sourceFingerprints=[
            SourceFingerprint(sourceEntity=f"firds:Instrument:{isin}", fingerprint=_fingerprint(doc))
        ],
        isActive=lifecycle == "active",
    )

    try:
        return FundGolden(
            goldenId=f"FG-{isin}-001",
            cfiCode=cfi,
            identifierList=identifier_list,
            longName=doc.get("gnr_full_name") or issuer["umbrellaName"],
            shortName=doc.get("gnr_short_name"),
            umbrella=umbrella,
            assetClass=asset_class_label,
            assetClassId=asset_class_id,
            fundSubType=fund_sub_type,
            primaryAssetClassExposure=primary_exposure,
            currencyOfDenomination=currency,
            domicile=issuer.get("country"),
            legalFramework=issuer.get("legalFramework"),
            legalStructure=issuer.get("legalStructure"),
            dividendPolicy=dividend_policy,
            lifecycleStatus=lifecycle,
            managementCompany=management_company,
            primaryListing=primary_listing,
            recordMeta=meta,
        )
    except ValidationError as exc:
        log.warning("validation failed for %s: %s", isin, exc.errors()[0]["msg"])
        return None


def write_ndjson(docs: List[FundGolden], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(doc.model_dump_json(exclude_none=True))
            fh.write("\n")
    return len(docs)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch UCITS funds from ESMA FIRDS and emit FundGolden NDJSON."
    )
    parser.add_argument(
        "--issuers", type=Path,
        help="Umbrella YAML override (default: bundled fund_umbrellas.yml).",
    )
    parser.add_argument(
        "--limit-per-issuer", type=int, default=None,
        help="Cap funds emitted per umbrella (smoke testing).",
    )
    parser.add_argument(
        "--limit-issuers", type=int, default=None,
        help="Cap number of umbrellas processed.",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("data/opensearch/golden/fund/funds.ndjson"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    issuers = load_issuers(args.issuers)
    if args.limit_issuers:
        issuers = issuers[: args.limit_issuers]
    log.info("Loaded %d umbrella(s)", len(issuers))

    run_id = f"firds-fund-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    all_docs: List[FundGolden] = []
    for i, issuer in enumerate(issuers, 1):
        lei = issuer["lei"]
        log.info("[%d/%d] %s (%s)", i, len(issuers), issuer["umbrellaName"], lei)
        records = list(iter_issuer_records(lei, FIRDS_FL))
        funds = dedupe_by_isin(iter(records))
        if args.limit_per_issuer:
            funds = funds[: args.limit_per_issuer]
        built = 0
        for raw in funds:
            golden = firds_to_golden(raw, issuer, run_id, now)
            if golden is not None:
                all_docs.append(golden)
                built += 1
        log.info("  → %d FundGolden built (from %d FIRDS records)", built, len(records))

    n = write_ndjson(all_docs, args.output)
    log.info("Wrote %d FundGolden documents to %s", n, args.output)


if __name__ == "__main__":
    main()
