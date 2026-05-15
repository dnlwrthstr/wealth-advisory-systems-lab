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


def row_to_golden(row: dict, run_id: str, now: datetime) -> Optional[BondGolden]:
    isin = row.get("isin")
    if not isin:
        return None
    currency_code = row.get("nominal_currency")
    maturity = row.get("maturity_date")
    if not currency_code or not maturity:
        return None

    issuer_country = row.get("issuer_country")
    country = Country(issuer_country) if issuer_country and len(issuer_country) == 2 else None

    issuer = IssuerSnapshot(
        issuerId=f"ISS-{row.get('issuer_name') or isin}",
        legalName=row.get("issuer_name") or isin,
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
            currentCouponRate=row.get("coupon_rate"),
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
        "--output", "-o", type=Path,
        default=Path("data/opensearch/golden/bond/bonds.ndjson"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    master = load_bond_master()
    log.info("Loaded %d bonds from data/universe/bond.parquet", len(master))
    if args.limit:
        master = master.head(args.limit)

    run_id = f"parquet-bond-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    docs = []
    for row in master.to_dict("records"):
        clean = {k: (v if v == v else None) for k, v in row.items()}  # NaN → None
        golden = row_to_golden(clean, run_id, now)
        if golden is not None:
            docs.append(golden)
    n = write_ndjson(docs, args.output)
    log.info("Wrote %d BondGolden documents to %s", n, args.output)


if __name__ == "__main__":
    main()
