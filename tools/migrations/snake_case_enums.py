"""One-shot migration: convert every non-snake_case enum value across the
project to snake_case.

Per-file-type strategy (avoids over-matching field names / class names / UI labels):

- **YAML** (`*.yml`)   — replace inside `enum:` list items (`- value`) and
  scalar examples (`example: value`, `default: value`, `enumDefault: value`).
- **Python** (`*.py`)  — replace only inside quoted string literals (`'V'`, `"V"`).
  This skips type annotations (`field: V`) and assignments to the LHS.
- **JSON/NDJSON**      — replace only when preceded by `: ` (value position),
  skipping JSON keys with the same spelling.
- **Frontend JSX/JS**  — replace inside string literals AND object-key form
  (`V:`), but skip the AMBIGUOUS tokens entirely since they collide heavily
  with UI labels (`title="Issuer"`).

Run from project root:
    python tools/migrations/snake_case_enums.py            # dry-run
    python tools/migrations/snake_case_enums.py --apply    # write changes
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Master mapping. Every entry was validated against the ontology survey.
# ---------------------------------------------------------------------------
MAPPING: dict[str, str] = {
    # AssetClass.valuationFrequency
    "adHoc": "ad_hoc",
    # BasketDefinition.basketType
    "bestOf": "best_of",
    "equalWeighted": "equal_weighted",
    "weightedAverage": "weighted_average",
    "worstOf": "worst_of",
    # BondGolden.bondSubType
    "corporateHighYield": "corporate_high_yield",
    "corporateInvestmentGrade": "corporate_investment_grade",
    "inflationLinked": "inflation_linked",
    "sovereignSupranational": "sovereign_supranational",
    "zeroCoupon": "zero_coupon",
    # BondGolden.maturityBucket — fully flattened per user
    "shortTerm_lt1y": "short_term_less_than_1y",
    "shortTerm_1y_3y": "short_term_1y_to_3y",
    "intermediate_3y_5y": "intermediate_3y_to_5y",
    "intermediate_5y_10y": "intermediate_5y_to_10y",
    "longTerm_10y_30y": "long_term_10y_to_30y",
    "veryLongTerm_gt30y": "very_long_term_greater_than_30y",
    # ComplianceFlags.mifid2TargetMarket (bond + equity + fund)
    "eligibleCounterparty": "eligible_counterparty",
    # EquityGolden.equitySubType / Equity.equitySubType
    "commonStock": "common_stock",
    "convertiblePreferred": "convertible_preferred",
    "preferredStock": "preferred_stock",
    # FundGolden ComplianceFlags
    "notApplicable": "not_applicable",
    # FundGolden.dealingFrequency / .rebalanceFrequency / paymentFrequency
    "semiAnnual": "semi_annual",
    "atMaturity": "at_maturity",
    # FundGolden.dividendPolicy (+ Fund.dividendPolicy)
    "ACCUMULATING": "accumulating",
    "DISTRIBUTING": "distributing",
    # FundGolden.fundStrategy
    "longShort": "long_short",
    "marketNeutral": "market_neutral",
    "passive_indexTracking": "passive_index_tracking",
    "smartBeta": "smart_beta",
    # FundGolden.fundSubType
    "closeEndedFund": "close_ended_fund",
    "fundOfFunds": "fund_of_funds",
    "hedgeFund": "hedge_fund",
    "moneyMarketFund": "money_market_fund",
    "openEndedMutualFund": "open_ended_mutual_fund",
    "privateEquity": "private_equity",
    "realEstateFund": "real_estate_fund",
    "structuredFund": "structured_fund",
    # FundGolden.lifecycleStatus extras
    "hardClosed": "hard_closed",
    "softClosed": "soft_closed",
    # FundGolden.primaryAssetClassExposure
    "fixedIncome": "fixed_income",
    "moneyMarket": "money_market",
    "realEstate": "real_estate",
    # FundGolden.replicationMethod
    "physicalFull": "physical_full",
    "physicalSampling": "physical_sampling",
    "syntheticSwap": "synthetic_swap",
    # Identifier.scheme / FinancialInstrumentIdentification.type
    "bloombergComposite": "bloomberg_composite",
    "bloombergTicker": "bloomberg_ticker",
    "otherProprietaryIdentification": "other_proprietary_identification",
    "tickerSymbol": "ticker_symbol",
    # InstrumentRef.instrumentType
    "structuredProduct": "structured_product",
    # ValuationSnapshot.priceType / ValuationPrice.priceType
    "askPrice": "ask_price",
    "bidPrice": "bid_price",
    "closingPrice": "closing_price",
    "meanPrice": "mean_price",
    # ClassificationAssignment.appliesTo.entityType
    "Instrument": "instrument",
    "Issuer": "issuer",
    "Listing": "listing",
    "Portfolio": "portfolio",
    # ClassificationSystem.classificationType
    "CustomClassification": "custom_classification",
    "IndustryClassification": "industry_classification",
    "SectorClassification": "sector_classification",
    "ThematicClassification": "thematic_classification",
    # CreditSupport
    "csaAgreement": "csa_agreement",
    "marginAgreement": "margin_agreement",
    # DayCountBasis — lowercase trailing letters per user
    "act_365L": "act_365l",
    "act_actAfb": "act_act_afb",
    "act_actIcma": "act_act_icma",
    "act_actIsda": "act_act_isda",
    "u30E_360": "u30e_360",
    "u30E_360Icma": "u30e_360_icma",
    "u30E_360Isda": "u30e_360_isda",
    "u30U_360": "u30u_360",
    # Quantity.type
    "amortisedValue": "amortised_value",
    "digitalTokenUnit": "digital_token_unit",
    "faceAmount": "face_amount",
    # IssuanceStatus
    "bookBuilding": "book_building",
    # Credit.creditType / .repaymentType
    "fixedTerm": "fixed_term",
    "lombardLoan": "lombard_loan",
    "interestOnly": "interest_only",
    # PolicyConstraint.constraintType
    "hedgeRatio": "hedge_ratio",
    "marginThreshold": "margin_threshold",
    "trackingErrorLimit": "tracking_error_limit",
    # PartnerType
    "advisoryUnit": "advisory_unit",
    "legalEntity": "legal_entity",
    "naturalPerson": "natural_person",
    # Account.type
    "cashAccount": "cash_account",
    "safekeepingAccount": "safekeeping_account",
    # CommonErrorType — user accepts breaking change
    "/problems/EXPIRED_TOKEN": "/problems/expired_token",
    "/problems/INSUFFICIENT_PRIVILEGES": "/problems/insufficient_privileges",
    "/problems/INVALID_PAYLOAD": "/problems/invalid_payload",
    "/problems/INVALID_TOKEN": "/problems/invalid_token",
    "/problems/MALFORMED_PAYLOAD": "/problems/malformed_payload",
    "/problems/NOT_IMPLEMENTED": "/problems/not_implemented",
    "/problems/NO_ACCESS_TO_RESOURCE": "/problems/no_access_to_resource",
    "/problems/OPERATION_NOT_ALLOWED": "/problems/operation_not_allowed",
    "/problems/RESOURCE_DOES_NOT_EXIST": "/problems/resource_does_not_exist",
    "/problems/RESOURCE_NOT_READY": "/problems/resource_not_ready",
    "/problems/RESOURCE_TOO_LARGE": "/problems/resource_too_large",
    "/problems/SERVICE_UNAVAILABLE": "/problems/service_unavailable",
    "/problems/TECHNICAL_ERROR": "/problems/technical_error",
    "/problems/WRONG_METHOD": "/problems/wrong_method",
    # PostingAmount.type
    "accruedInterest": "accrued_interest",
    "grossAmount": "gross_amount",
    "netAmount": "net_amount",
    # TransactionType
    "corporateAction": "corporate_action",
    "transferIn": "transfer_in",
    "transferOut": "transfer_out",
    # Cash.assetClassCategory
    "cashEquivalent": "cash_equivalent",
    "marginAccount": "margin_account",
    # CreditDefaultSwap.businessDayConvention / .restructuringType / .seniority
    "modifiedFollowing": "modified_following",
    "modifiedPreceding": "modified_preceding",
    "modifiedModified": "modified_modified",
    "modifiedRestructuring": "modified_restructuring",
    "noRestructuring": "no_restructuring",
    "oldRestructuring": "old_restructuring",
    "juniorSubordinated": "junior_subordinated",
    # ESGStandardReference.framework
    "EU_GreenBondStandard": "eu_green_bond_standard",
    "ICMA_GreenBondPrinciples": "icma_green_bond_principles",
    "ICMA_SocialBondPrinciples": "icma_social_bond_principles",
    # Python-only enums (custodian.schemas, orders.schemas) not in ontology survey
    "additionalPayment": "additional_payment",
    "additionalWithholdingTax": "additional_withholding_tax",
    "adjustNotional": "adjust_notional",
    "aggressiveGrowth": "aggressive_growth",
    "balancedGrowth": "balanced_growth",
    "brokerageFee": "brokerage_fee",
    "buyToClose": "buy_to_close",
    "capitalGainTax": "capital_gain_tax",
    "capitalGrowth": "capital_growth",
    "capitalIncrease": "capital_increase",
    "capitalPreservation": "capital_preservation",
    "closeContract": "close_contract",
    "creditEvent": "credit_event",
    "cryptoAsset": "crypto_asset",
    "custodyFee": "custody_fee",
    "decreasePrincipal": "decrease_principal",
    "deliveryFreeOfPayment": "delivery_free_of_payment",
    "deliveryVsPayment": "delivery_vs_payment",
    "dividendCash": "dividend_cash",
    "dividendChoice": "dividend_choice",
    "dividendReinvestment": "dividend_reinvestment",
    "dividendStock": "dividend_stock",
    "exchangeFee": "exchange_fee",
    "executionOnly": "execution_only",
    "familyOffice": "family_office",
    "finalLiquidationPayment": "final_liquidation_payment",
    "financialTransactionTax": "financial_transaction_tax",
    "fxForward": "fx_forward",
    "fxOption": "fx_option",
    "fxSpot": "fx_spot",
    "fxSwap": "fx_swap",
    "highNetWorth": "high_net_worth",
    "increasePrincipal": "increase_principal",
    "inflowCash": "inflow_cash",
    "instrumentExchange": "instrument_exchange",
    "interestPayment": "interest_payment",
    "internalTransfer": "internal_transfer",
    "liquidationPayment": "liquidation_payment",
    "managementFee": "management_fee",
    "openContract": "open_contract",
    "otherFee": "other_fee",
    "otherTax": "other_tax",
    "outflowCash": "outflow_cash",
    "preciousMetal": "precious_metal",
    "prepaymentSubstitution": "prepayment_substitution",
    "privateClient": "private_client",
    "receiveFreeOfPayment": "receive_free_of_payment",
    "receiveVsPayment": "receive_vs_payment",
    "reclaimableTax": "reclaimable_tax",
    "redemptionPartial": "redemption_partial",
    "redemptionPrior": "redemption_prior",
    "reductionOfNominal": "reduction_of_nominal",
    "reinvestmentAmount": "reinvestment_amount",
    "resetPayment": "reset_payment",
    "rightDistribution": "right_distribution",
    "sellToOpen": "sell_to_open",
    "spinOff": "spin_off",
    "stampDuty": "stamp_duty",
    "stockSplit": "stock_split",
    "stopLimit": "stop_limit",
    "taxCorrections": "tax_corrections",
    "thirdPartyFee": "third_party_fee",
    "transactionFee": "transaction_fee",
    "transferMetalPhysical": "transfer_metal_physical",
    "troyOunce": "troy_ounce",
    "ultraHighNetWorth": "ultra_high_net_worth",
    "valueAddedTax": "value_added_tax",
    "variationMargin": "variation_margin",
    "withholdingTax": "withholding_tax",
    # FinancialInstrumentType: simple/convertible bond + position types
    "simpleBond": "simple_bond",
    "convertibleBond": "convertible_bond",
    "bondPosition": "bond_position",
    "stockPosition": "stock_position",
    "cashPosition": "cash_position",
    "convertiblePosition": "convertible_position",
    "preferredPosition": "preferred_position",
    "otherPosition": "other_position",
}

# These four collide with class / type names everywhere (Issuer, Listing,
# Instrument, Portfolio). In frontend JSX they're also common UI labels
# (`title="Issuer"`). Restrict their replacement to YAML enum-list context only.
AMBIGUOUS = {"Instrument", "Issuer", "Listing", "Portfolio"}

# These collide with pydantic FIELD names that also happen to be enum values.
# In Python they appear as field declarations (`accruedInterest: Optional[...]`)
# AND as enum string literals (`"accruedInterest"`). The quote-only Python regex
# distinguishes them safely; we just list them here for documentation.
FIELD_COLLISIONS = {"accruedInterest", "hedgeRatio"}

SAFE_KEYS = sorted(
    (k for k in MAPPING if k not in AMBIGUOUS), key=lambda s: -len(s)
)
AMBIG_KEYS = sorted(AMBIGUOUS, key=lambda s: -len(s))
ALL_KEYS = sorted(MAPPING.keys(), key=lambda s: -len(s))


# ---------------------------------------------------------------------------
# Per-file-type patterns
# ---------------------------------------------------------------------------

# YAML: replace inside list items (`  - value`) or scalar fields
# (`key: value`, `example: value`, `default: value`). The lhs is end-of-line +
# indent + dash + space OR `<key>: `. The rhs is end-of-line / # comment.
_yaml_pattern = re.compile(
    r"(?P<lhs>(?:^[ \t]*-[ \t]+)|"  # YAML list item
    r"(?:^[ \t]*(?:example|default|enumDefault)[ \t]*:[ \t]+))"
    r"(?P<val>" + "|".join(re.escape(k) for k in ALL_KEYS) + r")"
    r"(?P<rhs>[ \t]*(?:#.*)?$)",
    re.MULTILINE,
)

# Inline YAML lists: `enum: [a, b, c]`. We match each value bounded by
# `[`, `,`, or whitespace and trailing `,`, `]`, or whitespace.
# Use lookahead on rhs so the comma is not consumed; otherwise the next
# scan starts past the comma and the following value doesn't match.
_yaml_inline_pattern = re.compile(
    r"(?P<lhs>[\[,][ \t]*)"
    r"(?P<val>" + "|".join(re.escape(k) for k in ALL_KEYS) + r")"
    r"(?=[ \t]*[\],])"
)

# Python: only inside quoted string literals (single/double/triple).
_python_pattern = re.compile(
    r"(?P<lhs>['\"`])"
    r"(?P<val>" + "|".join(re.escape(k) for k in SAFE_KEYS) + r")"
    r"(?P<rhs>['\"`])"
)

# JSON/NDJSON: only at value position (preceded by `: `, optionally with `[` for
# array-of-strings). Skips JSON keys.
_json_value_pattern = re.compile(
    r"(?P<lhs>(?::[ \t]*)|(?:,[ \t]*)|(?:\[[ \t]*))"
    r'"(?P<val>' + "|".join(re.escape(k) for k in SAFE_KEYS) + r')"'
)

# JSX/JS: replace in string literals AND object-key form (`KEY:`).
# Skip AMBIGUOUS — too many UI label collisions.
_jsx_string_pattern = re.compile(
    r"(?P<lhs>['\"`])"
    r"(?P<val>" + "|".join(re.escape(k) for k in SAFE_KEYS) + r")"
    r"(?P<rhs>['\"`])"
)
_jsx_objkey_pattern = re.compile(
    r"(?P<lhs>(?:^|[\{\(,;\n])[ \t]*)"
    r"(?P<val>" + "|".join(re.escape(k) for k in SAFE_KEYS) + r")"
    r"(?P<rhs>[ \t]*:)",
    re.MULTILINE,
)


def replace_yaml(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return m.group("lhs") + MAPPING[m.group("val")] + m.group("rhs")

    text = _yaml_pattern.sub(repl, text)

    def repl_inline(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return m.group("lhs") + MAPPING[m.group("val")]

    text = _yaml_inline_pattern.sub(repl_inline, text)
    return text, count


def replace_python(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return m.group("lhs") + MAPPING[m.group("val")] + m.group("rhs")

    return _python_pattern.sub(repl, text), count


def replace_json(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return m.group("lhs") + '"' + MAPPING[m.group("val")] + '"'

    return _json_value_pattern.sub(repl, text), count


def replace_jsx(text: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return m.group("lhs") + MAPPING[m.group("val")] + m.group("rhs")

    text = _jsx_string_pattern.sub(repl, text)
    text = _jsx_objkey_pattern.sub(repl, text)
    return text, count


def replace_for(p: Path, text: str) -> tuple[str, int]:
    suffix = p.suffix.lower()
    if suffix in (".yml", ".yaml"):
        return replace_yaml(text)
    if suffix == ".py":
        return replace_python(text)
    if suffix in (".json", ".ndjson"):
        return replace_json(text)
    if suffix in (".ts", ".tsx", ".js", ".jsx"):
        return replace_jsx(text)
    return text, 0


def iter_targets(root: Path) -> Iterable[Path]:
    patterns = [
        "ontology/**/*.yml",
        "src/**/*.py",
        "backend/**/*.py",
        "tests/**/*.py",
        "data/opensearch/golden/**/*.json",
        "data/opensearch/golden/**/*.ndjson",
        "frontend/src/**/*.ts",
        "frontend/src/**/*.tsx",
        "frontend/src/**/*.js",
        "frontend/src/**/*.jsx",
    ]
    excludes = {".venv", "node_modules", "__pycache__", ".git"}
    seen: set[Path] = set()
    for pat in patterns:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            if any(part in excludes for part in p.parts):
                continue
            if p in seen:
                continue
            seen.add(p)
            yield p


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    total_files = 0
    total_changes = 0
    file_summary: list[tuple[Path, int]] = []
    for p in iter_targets(root):
        old = p.read_text(encoding="utf-8")
        new, n = replace_for(p, old)
        if n == 0:
            continue
        total_files += 1
        total_changes += n
        file_summary.append((p.relative_to(root), n))
        if args.apply:
            p.write_text(new, encoding="utf-8")

    for rel, n in sorted(file_summary):
        print(f"  {n:>4}  {rel}")
    verb = "applied" if args.apply else "would change"
    print(f"\n{verb}: {total_changes} replacements across {total_files} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
