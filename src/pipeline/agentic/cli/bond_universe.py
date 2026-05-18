"""Batch loader for a bond universe via the agentic platform.

Reads the curated issuer-LEI list at
`src/pipeline/gold/data/bond_issuers.yml`, then for each LEI runs
`pipeline.gold._firds.iter_issuer_records(lei, FIRDS_FL)` to enumerate
bond ISINs from ESMA FIRDS, deduplicates by ISIN, and calls
`AGENTS["bond"].assemble_and_persist(client, identifier, status="in_universe")`
per ISIN. After each successful persist, the record is mirrored onto
`pms_golden_instrumentsearch` via
`pipeline.gold.search_index_build.index_search_hit` — same posture as
`POST /universe/bond` on instrument-api.

The loop is two-level (issuer → ISIN); the report groups outcomes per
issuer. Strict serial — one ISIN at a time. Per-ISIN errors are
isolated. Per-issuer FIRDS failures are also isolated (defensively;
`iter_issuer_records` already swallows persistent FIRDS errors and
returns an empty iterator, so a failed issuer shows up as "0 bonds"
rather than an exception).

Usage:

  PYTHONPATH=src python -m pipeline.agentic.cli.bond_universe \\
      [--issuer-lei LEI]            # single-issuer (mutually exclusive with --all)
      [--all]                       # process every issuer in bond_issuers.yml (default)
      [--issuers PATH]              # override the curated YAML
      [--limit-per-issuer N]        # cap bonds emitted per issuer
      [--dry-run]                   # skip persistence; report-only
      [--universe-status STATUS]    # default in_universe
      [--report-out PATH]           # write JSON report

The legacy `pipeline.gold.bond_firds --universe` CLI is being replaced
by this loader — see spec 002-agentic-bond-universe.
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

from pipeline.agentic.agents import AGENTS
from pipeline.agentic.persist import ALLOWED_UNIVERSE_STATUSES
from pipeline.gold._firds import iter_issuer_records
from pipeline.gold.bond_firds import FIRDS_FL, dedupe_by_isin, load_issuers

# `pipeline.gold.search_index_build` and `instruments.opensearch_store`
# pull in `opensearch-py`, which isn't always present in test
# environments. Import them lazily inside the functions that need them
# so the module is importable for argparse / report-shape testing.

log = logging.getLogger("bond_universe")

DEFAULT_UNIVERSE_STATUS = "in_universe"


@dataclass
class _Outcome:
    """Per-ISIN outcome captured for the run report."""

    issuer_lei: str
    isin: str
    status: str = "pending"  # success | partial | failed | skipped
    golden_id: Optional[str] = None
    quality_score: Optional[float] = None
    remaining_gaps: List[str] = field(default_factory=list)
    chained_issuers: int = 0
    reason: Optional[str] = None


@dataclass
class _IssuerReport:
    """Per-issuer roll-up nested inside the run report."""

    lei: str
    name: str
    isins_found: int = 0
    success: int = 0
    partial: int = 0
    failed: int = 0
    skipped: int = 0
    reason: Optional[str] = None  # set when the issuer-level FIRDS call returned nothing
    outcomes: List[_Outcome] = field(default_factory=list)


@dataclass
class _RunReport:
    requested_issuers: int = 0
    total_isins: int = 0
    success: int = 0
    partial: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_seconds: float = 0.0
    issuers: List[_IssuerReport] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requested_issuers": self.requested_issuers,
            "total_isins": self.total_isins,
            "success": self.success,
            "partial": self.partial,
            "failed": self.failed,
            "skipped": self.skipped,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "issuers": [
                {
                    "lei": ir.lei,
                    "name": ir.name,
                    "isins_found": ir.isins_found,
                    "success": ir.success,
                    "partial": ir.partial,
                    "failed": ir.failed,
                    "skipped": ir.skipped,
                    "reason": ir.reason,
                    "outcomes": [asdict(o) for o in ir.outcomes],
                }
                for ir in self.issuers
            ],
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.agentic.cli.bond_universe",
        description="Batch-load a bond universe via the agentic platform.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--issuer-lei",
        help="Process bonds for this single issuer LEI only.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Process every issuer in the curated YAML (default).",
    )
    parser.add_argument(
        "--issuers",
        type=Path,
        default=None,
        help="Override the curated issuer YAML (default: bundled bond_issuers.yml).",
    )
    parser.add_argument(
        "--limit-per-issuer",
        type=int,
        default=None,
        help="Cap the number of bonds processed per issuer (useful for smoke testing).",
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


def _filter_issuers(
    issuers: List[Dict[str, Any]], requested_lei: Optional[str]
) -> List[Dict[str, Any]]:
    """Apply `--issuer-lei` filter; raise if the LEI isn't in the active YAML."""
    if requested_lei is None:
        return issuers
    matches = [i for i in issuers if i.get("lei") == requested_lei]
    if not matches:
        known = sorted(i.get("lei", "?") for i in issuers)
        raise SystemExit(
            f"unknown issuer LEI: {requested_lei}\n"
            f"known LEIs in the active YAML:\n  " + "\n  ".join(known)
        )
    return matches


def _assemble_one(
    *,
    client: Any,
    issuer_lei: str,
    isin: str,
    universe_status: str,
    dry_run: bool,
) -> _Outcome:
    """Assemble + persist + mirror one ISIN."""
    outcome = _Outcome(issuer_lei=issuer_lei, isin=isin)

    if dry_run:
        outcome.status = "skipped"
        outcome.reason = "dry-run"
        return outcome

    try:
        result = AGENTS["bond"].assemble_and_persist(
            client=client,
            identifier={"kind": "isin", "value": isin},
            status=universe_status,
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
    # behaviour of POST /universe/bond on instrument-api.
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


def _process_issuer(
    *,
    client: Any,
    issuer: Dict[str, Any],
    universe_status: str,
    dry_run: bool,
    limit_per_issuer: Optional[int],
) -> _IssuerReport:
    """Enumerate bonds for one issuer and assemble each."""
    ir = _IssuerReport(lei=issuer["lei"], name=issuer.get("name", "?"))

    try:
        records = list(iter_issuer_records(ir.lei, FIRDS_FL))
    except Exception as exc:  # noqa: BLE001 — defensive: iter_issuer_records *should* swallow but does not guarantee
        ir.reason = f"firds: {type(exc).__name__}: {exc}"
        log.warning("issuer %s firds failure: %s", ir.lei, ir.reason)
        return ir

    isins: List[str] = []
    for entry in dedupe_by_isin(iter(records)):
        isin = entry.get("isin")
        if isin and isin not in isins:
            isins.append(isin)
    if limit_per_issuer is not None:
        isins = isins[:limit_per_issuer]
    ir.isins_found = len(isins)

    if not isins:
        ir.reason = "no bonds returned by FIRDS (or all filtered out)"
        log.info("issuer %s (%s): %s", ir.name, ir.lei, ir.reason)
        return ir

    for isin in isins:
        outcome = _assemble_one(
            client=client,
            issuer_lei=ir.lei,
            isin=isin,
            universe_status=universe_status,
            dry_run=dry_run,
        )
        ir.outcomes.append(outcome)
        log.info(
            "  [%s] %s gaps=%d issuers=%d%s",
            outcome.status,
            isin,
            len(outcome.remaining_gaps),
            outcome.chained_issuers,
            f" reason={outcome.reason}" if outcome.reason else "",
        )
        if outcome.status == "success":
            ir.success += 1
        elif outcome.status == "partial":
            ir.partial += 1
        elif outcome.status == "skipped":
            ir.skipped += 1
        else:
            ir.failed += 1
    return ir


def run(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    issuers = load_issuers(args.issuers)
    issuers = _filter_issuers(issuers, args.issuer_lei)
    log.info(
        "loading bonds for %d issuer(s) dry_run=%s", len(issuers), args.dry_run
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

    report = _RunReport(requested_issuers=len(issuers))
    start = time.time()
    for i, issuer in enumerate(issuers, 1):
        log.info(
            "[%d/%d] %s (%s)", i, len(issuers), issuer.get("name", "?"), issuer["lei"]
        )
        ir = _process_issuer(
            client=client,
            issuer=issuer,
            universe_status=args.universe_status,
            dry_run=args.dry_run,
            limit_per_issuer=args.limit_per_issuer,
        )
        report.issuers.append(ir)
        report.total_isins += ir.isins_found
        report.success += ir.success
        report.partial += ir.partial
        report.failed += ir.failed
        report.skipped += ir.skipped
        log.info(
            "  → issuer %s: %d bonds; success=%d partial=%d failed=%d skipped=%d",
            ir.lei,
            ir.isins_found,
            ir.success,
            ir.partial,
            ir.failed,
            ir.skipped,
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
        f"\nissuers={report.requested_issuers} "
        f"isins={report.total_isins} "
        f"success={report.success} "
        f"partial={report.partial} "
        f"failed={report.failed} "
        f"skipped={report.skipped} "
        f"elapsed={report.elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
