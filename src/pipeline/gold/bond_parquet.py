"""Build BondGolden NDJSON straight from data/universe/bond.parquet.

The bond master is populated by `scripts/ingest_universe.py` from the
FINFOX `csv_terms` data — coupon rate, maturity, seniority, ISIN/valor
and S&P-style rating per issuer are all real values from the export.
This bypasses FIRDS entirely for the lab's primary bond path; FIRDS
(`bond_firds`) remains useful when there's no parquet master available.

Issuer rating + agency from the parquet flow into
`BondGolden.issuer.creditProfile.issuerRatings` (a list per the
ontology, scoped to whatever agencies provided the rating).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from universe.models import (
    BondGolden,
    Country,
    CreditProfile,
    Currency,
    FinancialInstrumentIdentification,
    GoldenRecordMeta,
    IssuerSnapshot,
    LegalEntityIdentifier,
    ListingSnapshot,
    Rating,
    SourceAttribution,
)

from pipeline.silver import load_bond_master

log = logging.getLogger("bond_parquet")

SCHEMA_VERSION = "0.2.0"


def _lifecycle_from_maturity(maturity_iso: Optional[str]) -> str:
    if not maturity_iso:
        return "active"
    try:
        return "matured" if dt.date.fromisoformat(maturity_iso) < dt.date.today() else "active"
    except ValueError:
        return "active"


def _seniority_token(value: Optional[str]) -> str:
    if not value:
        return "other"
    return value


# Bond names canonically start with the coupon as a percentage:
#   "5.375 Republik Ungarn 23-33"   →  5.375%   →  0.05375 decimal
#   "0.875 NRW.BANK 19-34"          →  0.875%   →  0.00875 decimal
#   "0.11 CABEI 21-28"              →  0.11%    →  0.0011  decimal
#   "0 Korea Railroad 19-24"        →  0%       →  0.0
#   "var Alpiq Holding AG 2013-ff"  →  variable →  fall back to parquet value
_COUPON_FROM_NAME = re.compile(r"^\s*(\d+(?:\.\d+)?)\b")


def _normalize_coupon(name: Optional[str], coupon_rate: Any) -> Optional[float]:
    """Belt-and-suspenders coupon normalisation against the bond name.

    The bronze ingest (scripts/ingest_universe.py) now always divides by 100,
    so the parquet's `coupon_rate` is consistently a decimal fraction. This
    function is kept as a safety net in case (a) the bronze ingest reverts or
    (b) a future FINFOX export changes format. The bond name canonically
    starts with the coupon in percentage form ("5.375 Republik Ungarn",
    "0.11 CABEI", "10.25 Brazil 07-28"), which we trust as the source of
    truth when the parsed value disagrees with the parquet by more than the
    rounding margin.

    Fall back to a defensive divide-by-100 heuristic only when the name
    isn't parseable (variable-coupon "var Alpiq …", blank name).
    """
    if name:
        m = _COUPON_FROM_NAME.match(name)
        if m:
            try:
                return round(float(m.group(1)) / 100.0, 6)
            except (TypeError, ValueError):
                pass
    if coupon_rate is None:
        return None
    try:
        v = float(coupon_rate)
    except (TypeError, ValueError):
        return None
    # Defensive fallback for var-rate bonds where we couldn't parse the name:
    # any value > 0.20 can't be a real bond coupon as decimal (would be 20%+),
    # so treat as percentage. Imperfect but better than nothing.
    return round(v / 100.0, 6) if v > 0.20 else v


def _credit_profile(rating: Optional[str], agency: Optional[str]) -> Optional[CreditProfile]:
    if not rating:
        return None
    return CreditProfile(
        issuerRatings=[
            Rating(
                agency=agency or "S&P",
                rating=rating,
                ratingType="issuer_credit_rating",
                scale="long_term",
                status="active",
            )
        ]
    )


def row_to_golden(
    row: dict,
    run_id: str,
    now: datetime,
    *,
    enrich_lei: bool = False,
) -> Optional[BondGolden]:
    isin = row.get("isin")
    if not isin:
        return None
    currency_code = row.get("nominal_currency")
    maturity = row.get("maturity_date")
    if not currency_code or not maturity:
        return None

    issuer_country = row.get("issuer_country")
    country = Country(issuer_country) if issuer_country and len(issuer_country) == 2 else None

    # Best-effort LEI resolution via GLEIF's ISIN filter. When GLEIF has no
    # record (often the case for XS Eurobonds) we fall back to the
    # name-derived issuerId so the downstream aggregator still has something
    # to dedupe by.
    issuer_lei: Optional[str] = None
    if enrich_lei:
        from ._lei_lookup import lei_for_isin
        issuer_lei = lei_for_isin(isin)

    issuer_name = row.get("issuer_name") or isin
    if issuer_lei:
        issuer_id = f"ISS-{issuer_lei}"
    else:
        issuer_id = f"ISS-{issuer_name}"

    issuer = IssuerSnapshot(
        issuerId=issuer_id,
        legalName=issuer_name,
        lei=LegalEntityIdentifier(issuer_lei) if issuer_lei else None,
        issuerType="corporate" if (row.get("sector") not in (None, "Government", "Sovereign")) else "government",
        domicileCountry=country,
        headquartersCountry=country,
        creditProfile=_credit_profile(row.get("rating"), row.get("rating_agency")),
    )

    currency = Currency(currency_code)
    primary_listing = ListingSnapshot(
        mic="XOFF",  # parquet doesn't carry a venue; bonds are mostly OTC anyway
        listingCurrency=currency,
        status="active",
        isPrimary=True,
    )

    identifier_list = [FinancialInstrumentIdentification(identifier=isin, type="isin")]
    if row.get("valor_nr"):
        identifier_list.append(
            FinancialInstrumentIdentification(identifier=str(row["valor_nr"]), type="valoren")
        )

    meta = GoldenRecordMeta(
        schemaVersion=SCHEMA_VERSION,
        goldenAsOf=now.isoformat(),
        ingestionRunId=run_id,
        sourceOfTruth=[
            SourceAttribution(fieldGroup="identifiers", source="finfox-csv"),
            SourceAttribution(fieldGroup="terms", source="finfox-csv"),
            SourceAttribution(
                fieldGroup="issuerRating",
                source=row.get("rating_agency") or "finfox-csv",
            ),
        ],
        isActive=True,
    )

    try:
        return BondGolden(
            goldenId=f"BG-{isin}-001",
            identifierList=identifier_list,
            longName=row.get("name") or isin,
            assetClass=(
                "Fixed Income / Government Bond"
                if issuer.issuerType == "government"
                else "Fixed Income / Corporate Bond"
            ),
            assetClassId=(
                "AC-FI-GOVT"
                if issuer.issuerType == "government"
                else "AC-FI-CORP-IG"
            ),
            seniority=_seniority_token(row.get("seniority")),
            countryOfRisk=country,
            currencyOfDenomination=currency,
            maturityDate=maturity,
            couponType=row.get("interest_type") or None,
            currentCouponRate=_normalize_coupon(row.get("name"), row.get("coupon_rate")),
            minimumDenomination=row.get("face_value"),
            lifecycleStatus=_lifecycle_from_maturity(maturity),
            issuer=issuer,
            primaryListing=primary_listing,
            recordMeta=meta,
        )
    except ValidationError as exc:
        log.warning("validation failed for %s: %s", isin, exc.errors()[0]["msg"])
        return None


def write_ndjson(docs: list, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(doc.model_dump_json(exclude_none=True))
            fh.write("\n")
    return len(docs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build BondGolden NDJSON from data/universe/bond.parquet "
            "(real FINFOX terms + S&P ratings)."
        )
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Cap on number of bonds (smoke testing).",
    )
    parser.add_argument(
        "--enrich-lei", action="store_true",
        help=(
            "For each bond ISIN, look up the issuer LEI via the GLEIF "
            "filter[isin] endpoint (cached on disk). Slow first pass; "
            "subsequent runs use the cache. Eurobonds often have no GLEIF "
            "ISIN mapping — those keep the name-derived issuerId."
        ),
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        default=Path("data/opensearch/golden/bond/bonds.ndjson"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    master = load_bond_master()
    log.info("Loaded %d bonds from data/universe/bond.parquet", len(master))
    if args.limit:
        master = master.head(args.limit)
    if args.enrich_lei:
        log.info("GLEIF ISIN-LEI enrichment enabled (cached under ~/.cache/wealth-advisory-systems-lab/gleif-isin/)")

    run_id = f"parquet-bond-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    docs = []
    resolved = 0
    for i, row in enumerate(master.to_dict("records"), 1):
        clean = {k: (v if v == v else None) for k, v in row.items()}  # NaN → None
        golden = row_to_golden(clean, run_id, now, enrich_lei=args.enrich_lei)
        if golden is None:
            continue
        if golden.issuer.lei:
            resolved += 1
        docs.append(golden)
        if args.enrich_lei and i % 50 == 0:
            log.info("  [%d/%d] processed; %d LEIs resolved so far", i, len(master), resolved)
    if args.enrich_lei:
        log.info("LEI resolution: %d / %d bonds got an issuer LEI", resolved, len(docs))
    n = write_ndjson(docs, args.output)
    log.info("Wrote %d BondGolden documents to %s", n, args.output)


if __name__ == "__main__":
    main()
