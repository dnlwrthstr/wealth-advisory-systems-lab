"""Fetch bonds from ESMA FIRDS for a curated issuer list and emit
BondGolden NDJSON.

Per issuer LEI: query FIRDS Solr, paginate, filter to CFI category D
(debt), dedupe by ISIN (keeping the highest-quality record per ISIN),
build a validated `BondGolden` pydantic instance per surviving doc, and
write one document per line to NDJSON.

FIRDS populates static fields well (ISIN, CFI, coupon type, coupon rate,
maturity, denomination, seniority, primary venue). Prices / yields /
spreads / ratings need pricing-service and rating-agency feeds, so they
stay blank in the golden record.
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
    BondGolden,
    Currency,
    Country,
    FinancialInstrumentIdentification,
    GoldenRecordMeta,
    IssuerSnapshot,
    LegalEntityIdentifier,
    ListingSnapshot,
    SourceAttribution,
    SourceFingerprint,
)

from ._firds import iter_issuer_records, solr_get

log = logging.getLogger("bond_firds")

SCHEMA_VERSION = "0.1.0"

# FIRDS fields we ask Solr to return.
FIRDS_FL = [
    "isin", "lei",
    "gnr_full_name", "gnr_short_name", "gnr_cfi_code",
    "gnr_notional_curr_code",
    "bnd_maturity_date", "bnd_fixed_rate", "bnd_seniority",
    "bnd_nmnl_value_total", "bnd_nmnl_value_unit", "bnd_nmnl_value_curr_code",
    "mic", "rca_mic", "upcoming_rca",
    "mrkt_trdng_start_date", "mrkt_trdng_trmination_date",
    "status", "status_label", "valid_from_date",
]

SENIORITY_MAP: Dict[str, str] = {
    "SNDB": "senior_unsecured", "SNDS": "senior_unsecured", "SNDU": "senior_unsecured",
    "SNSB": "senior_secured",
    "SNNP": "senior_non_preferred",
    "SBOD": "subordinated", "JUND": "junior_subordinated",
    "MZZD": "other",
}

CFI_COUPON_TYPE: Dict[str, str] = {
    "F": "fixed", "V": "variable", "Z": "zero", "C": "fixed",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def derive_bond_sub_type(cfi: Optional[str], issuer_type: str) -> str:
    cfi = (cfi or "").upper().ljust(6, "X")
    if issuer_type == "government":
        return "government"
    if issuer_type == "supranational":
        return "sovereignSupranational"
    if issuer_type == "insurance_company":
        return "corporateInvestmentGrade"
    sub = cfi[1]
    if sub == "C":
        return "convertible"
    if sub == "Y":
        return "securitised"
    if sub in ("T", "B"):
        return "corporateInvestmentGrade"
    return "other"


def derive_coupon_type(cfi: Optional[str], fixed_rate: Any) -> Optional[str]:
    cfi = (cfi or "").upper().ljust(6, "X")
    if cfi[2] in CFI_COUPON_TYPE:
        return CFI_COUPON_TYPE[cfi[2]]
    if fixed_rate not in (None, "", "0", 0):
        return "fixed"
    return None


def _to_float(v: Any) -> Optional[float]:
    if v in (None, "", "N/A"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _iso_date(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v)
    return s.split("T", 1)[0] if "T" in s else s


def _lifecycle_status(status: Optional[str], maturity_date: Optional[str]) -> str:
    s = (status or "").upper()
    if s == "TERM":
        return "matured"
    if s == "CANC":
        return "inactive"
    if maturity_date:
        try:
            if dt.date.fromisoformat(maturity_date) < dt.date.today():
                return "matured"
        except ValueError:
            pass
    return "active"


def _fingerprint(doc: Dict[str, Any]) -> str:
    payload = json.dumps(doc, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Issuer resolution
# ---------------------------------------------------------------------------

def load_issuers(path: Optional[Path]) -> List[Dict[str, Any]]:
    if path is None:
        text = files("pipeline.gold.data").joinpath("bond_issuers.yml").read_text(encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    issuers = data.get("issuers") or []
    if not issuers:
        raise SystemExit("Empty issuer file.")
    for entry in issuers:
        if not entry.get("lei") or not entry.get("name"):
            raise SystemExit(f"issuer missing lei/name: {entry}")
        entry.setdefault("issuerType", "corporate")
        entry.setdefault("assetClass", "Fixed Income / Corporate Bond")
        entry.setdefault("assetClassId", "AC-FI-CORP-IG")
        entry.setdefault("_source", "curated-issuers.yml")
    return issuers


def _asset_class_defaults(issuer_type: str) -> Tuple[str, str]:
    if issuer_type == "government":
        return "Fixed Income / Government Bond", "AC-FI-GOVT"
    if issuer_type == "supranational":
        return "Fixed Income / Supranational Bond", "AC-FI-SUPRA"
    return "Fixed Income / Corporate Bond", "AC-FI-CORP-IG"


def _gleif_to_issuer(lei: str) -> Optional[Dict[str, Any]]:
    """Build an issuer dict for `lei` from GLEIF. None when GLEIF has nothing."""
    from pipeline.gold.issuer_gleif import fetch_gleif, gleif_fields

    record = fetch_gleif(lei)
    fields = gleif_fields(record) if record else {}
    if not fields.get("legalName"):
        return None
    issuer_type = fields.get("issuerTypeFromGleif") or "corporate"
    asset_class, asset_class_id = _asset_class_defaults(issuer_type)
    return {
        "lei": lei,
        "name": fields["legalName"],
        "issuerType": issuer_type,
        "country": fields.get("domicileCountry"),
        "assetClass": asset_class,
        "assetClassId": asset_class_id,
        "_source": "gleif",
    }


def _resolve_issuer(lei: str, issuers_path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Resolve issuer metadata for `lei`. Curated YAML overrides GLEIF.

    Falls back to GLEIF when the LEI isn't in the curated YAML — bonds whose
    issuers haven't been curated still assemble, with legal-entity attributes
    sourced from the same authority used by the issuer scope.
    """
    try:
        issuers = load_issuers(issuers_path)
    except SystemExit:
        issuers = []
    yaml_entry = next((i for i in issuers if i.get("lei") == lei), None)
    if yaml_entry is not None:
        return yaml_entry
    return _gleif_to_issuer(lei)


# ---------------------------------------------------------------------------
# Dedup + filter
# ---------------------------------------------------------------------------

def _record_quality(doc: Dict[str, Any]) -> Tuple[int, int]:
    status = (doc.get("status") or "").upper()
    status_rank = {"UNCH": 3, "NEWT": 3, "TERM": 1, "CANC": 0}.get(status, 2)
    field_rank = sum(1 for v in doc.values() if v not in (None, ""))
    return status_rank, field_rank


def dedupe_by_isin(records: Iterator[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for doc in records:
        cfi = (doc.get("gnr_cfi_code") or "").upper()
        if not cfi.startswith("D"):
            continue
        isin = doc.get("isin")
        if not isin:
            continue
        current = best.get(isin)
        if current is None or _record_quality(doc) > _record_quality(current):
            best[isin] = doc
    return list(best.values())


# ---------------------------------------------------------------------------
# FIRDS doc → BondGolden
# ---------------------------------------------------------------------------

def firds_to_golden(
    doc: Dict[str, Any],
    issuer: Dict[str, Any],
    run_id: str,
    now: datetime,
) -> Optional[BondGolden]:
    now_iso = now.isoformat()
    isin = doc["isin"]
    cfi = doc.get("gnr_cfi_code")
    currency_code = doc.get("gnr_notional_curr_code") or doc.get("bnd_nmnl_value_curr_code")
    maturity = _iso_date(doc.get("bnd_maturity_date"))
    if not currency_code or not maturity:
        return None  # BondGolden requires both

    coupon_rate = _to_float(doc.get("bnd_fixed_rate"))
    if coupon_rate is not None:
        # FIRDS reports coupon as percentage; ontology expects a decimal fraction.
        coupon_rate = coupon_rate / 100.0

    first_trading_date = _iso_date(doc.get("mrkt_trdng_start_date"))
    seniority = SENIORITY_MAP.get(doc.get("bnd_seniority") or "", "other")
    sub_type = derive_bond_sub_type(cfi, issuer["issuerType"])
    coupon_type = derive_coupon_type(cfi, doc.get("bnd_fixed_rate"))
    lifecycle = _lifecycle_status(doc.get("status"), maturity)

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

    issuer_source = issuer.get("_source", "curated-issuers.yml")
    meta = GoldenRecordMeta(
        schemaVersion=SCHEMA_VERSION,
        goldenAsOf=now_iso,
        ingestionRunId=run_id,
        sourceOfTruth=[
            SourceAttribution(fieldGroup="identifiers", source="esma-firds"),
            SourceAttribution(fieldGroup="classification", source="esma-firds"),
            SourceAttribution(fieldGroup="issuer", source=issuer_source),
            SourceAttribution(fieldGroup="primaryListing", source="esma-firds"),
        ],
        sourceFingerprints=[
            SourceFingerprint(sourceEntity=f"firds:Instrument:{isin}", fingerprint=_fingerprint(doc))
        ],
        isActive=True,
    )

    issuer_snapshot = IssuerSnapshot(
        issuerId=f"ISS-{issuer['lei']}",
        legalName=issuer["name"],
        lei=LegalEntityIdentifier(issuer["lei"]),
        issuerType=issuer["issuerType"],
        domicileCountry=country,
        headquartersCountry=country,
    )

    try:
        return BondGolden(
            goldenId=f"BG-{isin}-001",
            cfiCode=cfi,
            identifierList=identifier_list,
            longName=doc.get("gnr_full_name") or issuer["name"],
            shortName=doc.get("gnr_short_name"),
            assetClass=issuer["assetClass"],
            assetClassId=issuer["assetClassId"],
            bondSubType=sub_type,
            seniority=seniority,
            countryOfRisk=country,
            currencyOfDenomination=currency,
            maturityDate=maturity,
            couponType=coupon_type,
            currentCouponRate=coupon_rate,
            minimumDenomination=_to_float(doc.get("bnd_nmnl_value_unit")),
            lifecycleStatus=lifecycle,
            issuer=issuer_snapshot,
            primaryListing=primary_listing,
            recordMeta=meta,
        )
    except ValidationError as exc:
        log.warning("validation failed for %s: %s", isin, exc.errors()[0]["msg"])
        return None


def _solr_query_by_isin(isin: str) -> List[Dict[str, Any]]:
    """Query FIRDS Solr for a single ISIN, return the (small) doc list."""
    params = {
        "q": f"isin:{isin}+AND+latest_received_flag:1",
        "wt": "json",
        "rows": "50",
        "start": "0",
        "fl": ",".join(FIRDS_FL),
        "sort": "valid_from_date desc",
    }
    data = solr_get(params)
    return list((data.get("response") or {}).get("docs", []))


def fetch_by_isin(
    isin: str,
    *,
    run_id: Optional[str] = None,
    now: Optional[datetime] = None,
    issuers_path: Optional[Path] = None,
) -> Optional[BondGolden]:
    """Query FIRDS for `isin`, resolve the issuer, build a BondGolden.

    Issuer resolution prefers the curated `data/bond_issuers.yml` (where it
    can carry custom assetClass labels) and falls back to GLEIF when the LEI
    is absent — so an arbitrary FIRDS-listed bond assembles end-to-end
    without manual curation. Returns None only if FIRDS has no debt record
    for the ISIN, or the FIRDS record carries no LEI, or neither the YAML
    nor GLEIF can identify the issuer.
    """
    docs = [d for d in _solr_query_by_isin(isin) if (d.get("gnr_cfi_code") or "").upper().startswith("D")]
    if not docs:
        return None
    doc = max(docs, key=_record_quality)
    lei = doc.get("lei")
    if not lei:
        log.info("isin %s: FIRDS record has no LEI — skipping", isin)
        return None
    issuer = _resolve_issuer(lei, issuers_path)
    if issuer is None:
        log.info("isin %s: issuer LEI %s not in curated yaml and not in GLEIF — skipping", isin, lei)
        return None
    run_id = run_id or f"firds-bond-{uuid.uuid4().hex[:8]}"
    now = now or datetime.now(timezone.utc)
    return firds_to_golden(doc, issuer, run_id, now)


def write_ndjson(docs: List[BondGolden], path: Path) -> int:
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
        description="Fetch bonds from ESMA FIRDS and emit BondGolden NDJSON."
    )
    parser.add_argument(
        "--issuers", type=Path,
        help="Issuer YAML override (default: bundled bond_issuers.yml).",
    )
    parser.add_argument(
        "--limit-per-issuer", type=int, default=None,
        help="Cap bonds emitted per issuer (smoke testing).",
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("data/opensearch/golden/bond/bonds.ndjson"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    issuers = load_issuers(args.issuers)
    log.info("Loaded %d issuer(s)", len(issuers))

    run_id = f"firds-bond-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    all_docs: List[BondGolden] = []
    for i, issuer in enumerate(issuers, 1):
        lei = issuer["lei"]
        log.info("[%d/%d] %s (%s)", i, len(issuers), issuer["name"], lei)
        records = list(iter_issuer_records(lei, FIRDS_FL))
        bonds = dedupe_by_isin(iter(records))
        if args.limit_per_issuer:
            bonds = bonds[: args.limit_per_issuer]
        built = 0
        for raw in bonds:
            golden = firds_to_golden(raw, issuer, run_id, now)
            if golden is not None:
                all_docs.append(golden)
                built += 1
        log.info("  → %d BondGolden built (from %d FIRDS records)", built, len(records))

    n = write_ndjson(all_docs, args.output)
    log.info("Wrote %d BondGolden documents to %s", n, args.output)


if __name__ == "__main__":
    main()
