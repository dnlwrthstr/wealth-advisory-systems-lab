"""Batch loader for an equity universe via the agentic platform.

Resolves a named ticker universe (SMI, S&P 500, NASDAQ 100, DAX 40,
FTSE 100) to a list of tickers via `pipeline.agentic.universes`, maps
each to an ISIN (OpenFIGI ticker-direction lookup for foreign venues;
SIX-listed Swiss tickers fall back to the planner's `six_ticker_isin`
source), and calls `EquityAgent.assemble_and_persist` per ISIN with
`universe_status="in_universe"` so the loaded records are marked as
part of the investable PMS universe.

After each successful persist the record is mirrored onto
`pms_golden_instrumentsearch` via
`pipeline.gold.search_index_build.index_search_hit` so the new record
surfaces in "Find an instrument" immediately — matching the behaviour
of `POST /universe/equity` on instrument-api.

Strict serial — one ISIN at a time. Naturally respects OpenFIGI's
per-minute quota (25 free / 250 with OPENFIGI_API_KEY). Per-ISIN
failures are isolated and reported; the batch does not abort on the
first error.

Usage:

  PYTHONPATH=src python -m pipeline.agentic.cli.equity_universe \\
      --universe smi          # one of: smi, sp500, nasdaq100, dax40, ftse100
      [--limit N]             # cap ISINs processed (smoke testing)
      [--dry-run]              # skip persistence; report-only
      [--no-cache]             # force fresh Wikipedia fetch
      [--universe-status STATUS]  # default in_universe
      [--report-out PATH]      # write JSON report
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

from pipeline.agentic import universes
from pipeline.agentic.agents import AGENTS
from pipeline.agentic.persist import ALLOWED_UNIVERSE_STATUSES

# `pipeline.gold.search_index_build` and `instruments.opensearch_store`
# pull in `opensearchpy`, which isn't always present in lightweight test
# environments. Import them lazily inside the functions that need them
# so the module is importable for argparse / report-shape testing
# regardless.

log = logging.getLogger("equity_universe")

DEFAULT_UNIVERSE_STATUS = "in_universe"


@dataclass
class _Outcome:
    """Per-input outcome captured for the run report."""

    ticker: str
    isin: Optional[str] = None
    status: str = "pending"  # one of: success, partial, failed, skipped
    golden_id: Optional[str] = None
    quality_score: Optional[float] = None
    remaining_gaps: List[str] = field(default_factory=list)
    chained_issuers: int = 0
    reason: Optional[str] = None


@dataclass
class _RunReport:
    universe: str
    requested: int
    success: int = 0
    partial: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_seconds: float = 0.0
    outcomes: List[_Outcome] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "universe": self.universe,
            "requested": self.requested,
            "success": self.success,
            "partial": self.partial,
            "failed": self.failed,
            "skipped": self.skipped,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "outcomes": [asdict(o) for o in self.outcomes],
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline.agentic.cli.equity_universe",
        description="Batch-load an equity universe via the agentic platform.",
    )
    parser.add_argument(
        "--universe",
        required=True,
        choices=universes.supported_universes(),
        help="Named ticker universe (Wikipedia-sourced).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of tickers processed (useful for smoke testing).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and report only; skip persistence.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force a fresh Wikipedia fetch (bypass the 7-day cache).",
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


def _resolve_and_assemble(
    *,
    client: Any,
    ticker: str,
    universe_status: str,
    dry_run: bool,
) -> _Outcome:
    """Resolve one ticker → ISIN, then assemble + persist + mirror search."""
    outcome = _Outcome(ticker=ticker)

    resolution = universes.tickers_to_isins([ticker])[0]
    if resolution.isin is not None:
        identifier = {"kind": "isin", "value": resolution.isin}
        outcome.isin = resolution.isin
    else:
        # Fall back to ticker — planner's six_ticker_isin handles SIX
        # listings. Foreign venues may still fail to resolve; that
        # surfaces as a partial / failed outcome below.
        identifier = {"kind": "ticker", "value": ticker}

    if dry_run:
        outcome.status = "skipped"
        outcome.reason = f"dry-run; identifier={identifier['kind']}={identifier['value']}"
        return outcome

    try:
        result = AGENTS["equity"].assemble_and_persist(
            client=client,
            identifier=identifier,
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
    # non-fatal: the universe write already succeeded; a stale search
    # mirror is recoverable, a lost universe write is not. Matches the
    # behaviour of POST /universe/equity on instrument-api.
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


def run(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    tickers = universes.resolve(args.universe, use_cache=not args.no_cache)
    if args.limit is not None:
        tickers = tickers[: args.limit]

    report = _RunReport(universe=args.universe, requested=len(tickers))
    log.info("loading universe=%s tickers=%d dry_run=%s", args.universe, len(tickers), args.dry_run)

    client = None
    if not args.dry_run:
        from instruments.opensearch_store import opensearch_client_from_env

        client = opensearch_client_from_env()
        if client is None:
            log.error("OPENSEARCH_URL not set — cannot persist. Use --dry-run for offline runs.")
            return 2

    start = time.time()
    for ticker in tickers:
        outcome = _resolve_and_assemble(
            client=client,
            ticker=ticker,
            universe_status=args.universe_status,
            dry_run=args.dry_run,
        )
        report.outcomes.append(outcome)
        log.info(
            "[%s] %s isin=%s gaps=%d issuers=%d%s",
            outcome.status,
            outcome.ticker,
            outcome.isin or "-",
            len(outcome.remaining_gaps),
            outcome.chained_issuers,
            f" reason={outcome.reason}" if outcome.reason else "",
        )
        if outcome.status == "success":
            report.success += 1
        elif outcome.status == "partial":
            report.partial += 1
        elif outcome.status == "skipped":
            report.skipped += 1
        else:
            report.failed += 1

    report.elapsed_seconds = time.time() - start

    print(_format_summary(report))

    if args.report_out is not None:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        log.info("wrote report to %s", args.report_out)

    return 0 if report.failed == 0 else 1


def _format_summary(report: _RunReport) -> str:
    return (
        f"\nuniverse={report.universe} "
        f"requested={report.requested} "
        f"success={report.success} "
        f"partial={report.partial} "
        f"failed={report.failed} "
        f"skipped={report.skipped} "
        f"elapsed={report.elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
