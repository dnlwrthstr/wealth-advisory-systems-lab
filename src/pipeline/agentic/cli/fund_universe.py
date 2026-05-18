"""Batch loader for a fund universe via the agentic platform.

Reads the curated umbrella-LEI list at
`src/pipeline/gold/data/fund_umbrellas.yml`, then for each umbrella LEI
runs `pipeline.gold._firds.iter_issuer_records(lei, FIRDS_FL)` to
enumerate share-class ISINs from ESMA FIRDS (filtered to CFI=C* via
`fund_firds.dedupe_by_isin`), and calls
`AGENTS["fund"].assemble_and_persist(client, identifier, status="in_universe", max_cost_class=...)`
per ISIN. After each successful persist, the record is mirrored onto
`pms_golden_instrumentsearch` via
`pipeline.gold.search_index_build.index_search_hit` — same posture as
`POST /universe/fund` on instrument-api.

Cost-class control (unique to fund vs equity/bond): `FundAgent`'s
default `max_cost_class` is `"llm_skill"`, which makes the
`find-and-parse-factsheet` skill eligible to fire on every fund
assemble. This CLI **overrides** the default to `"web_fetch"` so a
full universe load is free at the LLM layer. The
`--enable-factsheet-skill` flag opts back into `"llm_skill"` for runs
where you want TER, SRRI/SRI, dealing terms, and service-provider
enrichment from KIDs / factsheets. Pre-curated patches under
`data/opensearch/golden/fund/patches/*.json` are honoured by the
`fund_factsheet_patch` source regardless (cheap, `file_read`) — the
LLM only fires when a patch is missing AND the cap allows it.

The loop is two-level (umbrella → share-class ISIN); the report
groups outcomes per umbrella. Per-ISIN errors are isolated.
Umbrella-level FIRDS failures are also isolated; `iter_issuer_records`
swallows persistent FIRDS errors internally (retry-then-empty).

Usage:

  PYTHONPATH=src python -m pipeline.agentic.cli.fund_universe \\
      [--umbrella-lei LEI]          # single-umbrella (mutually exclusive with --all)
      [--all]                       # process every umbrella in fund_umbrellas.yml (default)
      [--umbrellas PATH]            # override the curated YAML
      [--limit-per-umbrella N]      # cap share-classes emitted per umbrella
      [--enable-factsheet-skill]    # opt into LLM cost (default: web_fetch cap)
      [--dry-run]                   # skip persistence; report-only
      [--universe-status STATUS]    # default in_universe
      [--report-out PATH]           # write JSON report

The legacy `pipeline.gold.fund_firds --universe` CLI is being replaced
by this loader — see spec 003-agentic-fund-universe.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load project-root .env so any source credentials (ANTHROPIC_API_KEY for
# the factsheet skill, plus the other source keys) are available to the
# agentic chain when this CLI runs outside Docker.
load_dotenv()

from pipeline.agentic.agents import AGENTS
from pipeline.agentic.persist import ALLOWED_UNIVERSE_STATUSES
from pipeline.gold._firds import iter_issuer_records
from pipeline.gold.fund_firds import FIRDS_FL, dedupe_by_isin, load_issuers

# `pipeline.gold.search_index_build` and `instruments.opensearch_store`
# pull in `opensearch-py`, which isn't always present in test
# environments. Import them lazily inside the functions that need them
# so the module is importable for argparse / report-shape testing.

log = logging.getLogger("fund_universe")

DEFAULT_UNIVERSE_STATUS = "in_universe"
COST_CLASS_DEFAULT = "web_fetch"          # cost-safe default for the CLI
COST_CLASS_WITH_SKILL = "llm_skill"       # opt-in via --enable-factsheet-skill


@dataclass
class _Outcome:
    """Per-share-class outcome captured for the run report."""

    umbrella_lei: str
    isin: str
    status: str = "pending"  # success | partial | failed | skipped
    golden_id: Optional[str] = None
    quality_score: Optional[float] = None
    remaining_gaps: List[str] = field(default_factory=list)
    chained_issuers: int = 0  # 1-3 for funds (umbrella + managementCompany + promoter)
    reason: Optional[str] = None


@dataclass
class _UmbrellaReport:
    """Per-umbrella roll-up nested inside the run report."""

    lei: str
    name: str
    isins_found: int = 0
    success: int = 0
    partial: int = 0
    failed: int = 0
    skipped: int = 0
    reason: Optional[str] = None  # set when the per-umbrella FIRDS call returned nothing
    outcomes: List[_Outcome] = field(default_factory=list)


@dataclass
class _RunReport:
    requested_umbrellas: int = 0
    total_isins: int = 0
    success: int = 0
    partial: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_seconds: float = 0.0
    cost_class: str = COST_CLASS_DEFAULT
    umbrellas: List[_UmbrellaReport] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requested_umbrellas": self.requested_umbrellas,
            "total_isins": self.total_isins,
            "success": self.success,
            "partial": self.partial,
            "failed": self.failed,
            "skipped": self.skipped,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "cost_class": self.cost_class,
            "umbrellas": [
                {
                    "lei": u.lei,
                    "name": u.name,
                    "isins_found": u.isins_found,
                    "success": u.success,
                    "partial": u.partial,
                    "failed": u.failed,
                    "skipped": u.skipped,
                    "reason": u.reason,
                    "outcomes": [asdict(o) for o in u.outcomes],
                }
                for u in self.umbrellas
            ],
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.agentic.cli.fund_universe",
        description="Batch-load a fund universe via the agentic platform.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--umbrella-lei",
        help="Process share-classes for this single umbrella LEI only.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Process every umbrella in the curated YAML (default).",
    )
    parser.add_argument(
        "--umbrellas",
        type=Path,
        default=None,
        help="Override the curated umbrella YAML (default: bundled fund_umbrellas.yml).",
    )
    parser.add_argument(
        "--limit-per-umbrella",
        type=int,
        default=None,
        help="Cap the number of share-classes processed per umbrella (useful for smoke testing).",
    )
    parser.add_argument(
        "--enable-factsheet-skill",
        action="store_true",
        help=(
            "Opt into the find-and-parse-factsheet LLM skill "
            "(max_cost_class=llm_skill). Default caps at web_fetch — no LLM tokens spend."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and report only; skip persistence.",
    )
    parser.add_argument(
        "--universe-status",
        default=DEFAULT_UNIVERSE_STATUS,
        choices=sorted(ALLOWED_UNIVERSE_STATUSES),
        help=f"universeStatus to stamp on persisted records (default: {DEFAULT_UNIVERSE_STATUS}).",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Write the run report as JSON to this path.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def _filter_umbrellas(
    umbrellas: List[Dict[str, Any]], requested_lei: Optional[str]
) -> List[Dict[str, Any]]:
    """Apply `--umbrella-lei` filter; raise SystemExit if the LEI isn't in the active YAML."""
    if requested_lei is None:
        return umbrellas
    matches = [u for u in umbrellas if u.get("umbrellaLei") == requested_lei]
    if not matches:
        known = sorted(u.get("umbrellaLei", "?") for u in umbrellas)
        raise SystemExit(
            f"unknown umbrella LEI: {requested_lei}\n"
            f"known LEIs in the active YAML:\n  " + "\n  ".join(known)
        )
    return matches


def _assemble_one(
    *,
    client: Any,
    umbrella_lei: str,
    isin: str,
    universe_status: str,
    max_cost_class: str,
    dry_run: bool,
) -> _Outcome:
    """Assemble + persist + mirror one share-class ISIN."""
    outcome = _Outcome(umbrella_lei=umbrella_lei, isin=isin)

    if dry_run:
        outcome.status = "skipped"
        outcome.reason = "dry-run"
        return outcome

    try:
        result = AGENTS["fund"].assemble_and_persist(
            client=client,
            identifier={"kind": "isin", "value": isin},
            status=universe_status,
            max_cost_class=max_cost_class,
        )
    except Exception as exc:  # noqa: BLE001 — broad: any source can raise
        outcome.status = "failed"
        outcome.reason = f"{type(exc).__name__}: {exc}"
        return outcome

    primary = result["primary"]
    outcome.golden_id = primary.record.get("goldenId")
    outcome.quality_score = primary.quality_score
    outcome.remaining_gaps = list(primary.remaining_gaps)
    outcome.chained_issuers = len(result["chained_issuers"])

    # Mirror onto the Find-an-instrument helper index. Failures here are
    # non-fatal — the universe write already succeeded. Matches the
    # behaviour of POST /universe/fund on instrument-api.
    try:
        from pipeline.gold.search_index_build import index_search_hit

        index_search_hit(
            client,
            primary.scope,
            primary.record,
            universe_status=universe_status,
        )
    except Exception as exc:  # noqa: BLE001 — broad: opensearchpy diverse errors
        log.warning(
            "search-index mirror failed for %s: %s", outcome.golden_id, exc
        )

    outcome.status = "partial" if outcome.remaining_gaps else "success"
    return outcome


def _process_umbrella(
    *,
    client: Any,
    umbrella: Dict[str, Any],
    universe_status: str,
    max_cost_class: str,
    dry_run: bool,
    limit_per_umbrella: Optional[int],
) -> _UmbrellaReport:
    """Enumerate share-classes for one umbrella and assemble each."""
    ur = _UmbrellaReport(
        lei=umbrella["umbrellaLei"],
        name=umbrella.get("umbrellaName", "?"),
    )

    try:
        records = list(iter_issuer_records(ur.lei, FIRDS_FL))
    except Exception as exc:  # noqa: BLE001 — defensive
        ur.reason = f"firds: {type(exc).__name__}: {exc}"
        log.warning("umbrella %s firds failure: %s", ur.lei, ur.reason)
        return ur

    isins: List[str] = []
    for entry in dedupe_by_isin(iter(records)):
        isin = entry.get("isin")
        if isin and isin not in isins:
            isins.append(isin)
    if limit_per_umbrella is not None:
        isins = isins[:limit_per_umbrella]
    ur.isins_found = len(isins)

    if not isins:
        ur.reason = "no share-classes returned by FIRDS (or all filtered out)"
        log.info("umbrella %s (%s): %s", ur.name, ur.lei, ur.reason)
        return ur

    for isin in isins:
        outcome = _assemble_one(
            client=client,
            umbrella_lei=ur.lei,
            isin=isin,
            universe_status=universe_status,
            max_cost_class=max_cost_class,
            dry_run=dry_run,
        )
        ur.outcomes.append(outcome)
        log.info(
            "  [%s] %s gaps=%d issuers=%d%s",
            outcome.status,
            isin,
            len(outcome.remaining_gaps),
            outcome.chained_issuers,
            f" reason={outcome.reason}" if outcome.reason else "",
        )
        if outcome.status == "success":
            ur.success += 1
        elif outcome.status == "partial":
            ur.partial += 1
        elif outcome.status == "skipped":
            ur.skipped += 1
        else:
            ur.failed += 1
    return ur


def run(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    max_cost_class = COST_CLASS_WITH_SKILL if args.enable_factsheet_skill else COST_CLASS_DEFAULT

    umbrellas = load_issuers(args.umbrellas)
    umbrellas = _filter_umbrellas(umbrellas, args.umbrella_lei)
    log.info(
        "loading funds for %d umbrella(s) dry_run=%s cost_class=%s",
        len(umbrellas), args.dry_run, max_cost_class,
    )

    client = None
    if not args.dry_run:
        from instruments.opensearch_store import opensearch_client_from_env

        client = opensearch_client_from_env()
        if client is None:
            log.error(
                "OPENSEARCH_URL not set — cannot persist. Use --dry-run for offline runs."
            )
            return 2

    report = _RunReport(
        requested_umbrellas=len(umbrellas),
        cost_class=max_cost_class,
    )
    start = time.time()
    for i, umbrella in enumerate(umbrellas, 1):
        log.info(
            "[%d/%d] %s (%s)",
            i, len(umbrellas),
            umbrella.get("umbrellaName", "?"),
            umbrella["umbrellaLei"],
        )
        ur = _process_umbrella(
            client=client,
            umbrella=umbrella,
            universe_status=args.universe_status,
            max_cost_class=max_cost_class,
            dry_run=args.dry_run,
            limit_per_umbrella=args.limit_per_umbrella,
        )
        report.umbrellas.append(ur)
        report.total_isins += ur.isins_found
        report.success += ur.success
        report.partial += ur.partial
        report.failed += ur.failed
        report.skipped += ur.skipped
        log.info(
            "  → umbrella %s: %d share-classes; success=%d partial=%d failed=%d skipped=%d",
            ur.lei,
            ur.isins_found,
            ur.success,
            ur.partial,
            ur.failed,
            ur.skipped,
        )

    report.elapsed_seconds = time.time() - start

    print(_format_summary(report))

    if args.report_out is not None:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(
            json.dumps(report.to_dict(), indent=2), encoding="utf-8"
        )
        log.info("wrote report to %s", args.report_out)

    return 0 if report.failed == 0 else 1


def _format_summary(report: _RunReport) -> str:
    return (
        f"\numbrellas={report.requested_umbrellas} "
        f"isins={report.total_isins} "
        f"success={report.success} "
        f"partial={report.partial} "
        f"failed={report.failed} "
        f"skipped={report.skipped} "
        f"cost_class={report.cost_class} "
        f"elapsed={report.elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
