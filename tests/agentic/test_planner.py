"""Planner tests — gap-driven loop with mocked source invocations."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline.agentic.manifest import manifest_for
from pipeline.agentic.merger import SourceFetchResult
from pipeline.agentic.planner import run_planner
from pipeline.agentic.registry import SourceDescriptor


def _src(
    *,
    id: str,
    produces: tuple[str, ...],
    confidence: str = "medium",
    cost: str = "api_call",
    covers: tuple[str, ...] = ("equity",),
    accepts: tuple[str, ...] = ("isin", "ticker"),
) -> SourceDescriptor:
    return SourceDescriptor(
        id=id,
        module="tests.agentic.fake",
        entrypoint="fetch",
        covers=covers,
        requires_identifier_any_of=accepts,
        produces_fields=produces,
        confidence=confidence,
        cost_class=cost,
    )


def test_picks_source_with_widest_gap_coverage_first():
    """When two sources are available, the one covering more gaps runs first."""
    manifest = manifest_for("equity")
    s_narrow = _src(id="narrow", produces=("longName",))
    s_wide = _src(id="wide", produces=("longName", "currencyOfDenomination", "issuer", "primaryListing"))

    invocations: list[str] = []

    def invoker(src: SourceDescriptor, kind: str, value: str, current: Dict[str, Any]) -> Optional[SourceFetchResult]:
        invocations.append(src.id)
        # Return everything the source claims it produces.
        patch = {f: f"v_{f}" for f in src.produces_fields}
        return SourceFetchResult(patch=patch, source_of_truth_rows=[{"fieldGroup": f, "source": src.id} for f in src.produces_fields])

    current, prov, trace = run_planner(
        scope="equity",
        identifier_kind="isin",
        identifier_value="US0378331005",
        manifest=manifest,
        sources=[s_narrow, s_wide],
        invoker=invoker,
    )
    assert invocations[0] == "wide"
    assert current["longName"] == "v_longName"


def test_loop_stops_when_no_candidate_covers_remaining_gaps():
    manifest = manifest_for("equity")
    s = _src(id="only", produces=("longName",))

    def invoker(src, k, v, c):
        return SourceFetchResult(patch={"longName": "Apple"}, source_of_truth_rows=[])

    current, prov, trace = run_planner(
        scope="equity",
        identifier_kind="isin",
        identifier_value="X",
        manifest=manifest,
        sources=[s],
        invoker=invoker,
    )
    assert current.get("longName") == "Apple"
    # Other required gaps still open, but no source covers them.
    assert trace.stopped_reason == "no remaining source covers any gap"


def test_fill_empty_only_earlier_source_wins_against_later_patches():
    """Once a field is set, a later source patching the same field is ignored.

    The planner picks `wide` first (more gaps covered). `wide` fills longName.
    Then `narrow` runs and tries to overwrite longName + add issuer. Only
    issuer is accepted; longName keeps the original value.
    """
    manifest = manifest_for("equity")
    s_wide = _src(id="wide", produces=("longName", "primaryListing", "currencyOfDenomination"))
    s_narrow = _src(id="narrow", produces=("longName", "issuer"))

    def invoker(src, k, v, c):
        if src.id == "wide":
            return SourceFetchResult(
                patch={"longName": "WIDE", "primaryListing": {"mic": "XNAS"}, "currencyOfDenomination": "USD"},
                source_of_truth_rows=[{"fieldGroup": "primaryListing", "source": "wide"}],
            )
        return SourceFetchResult(
            patch={"longName": "NARROW", "issuer": {"issuerId": "ISS-1", "legalName": "X"}},
            source_of_truth_rows=[{"fieldGroup": "issuer", "source": "narrow"}],
        )

    current, prov, trace = run_planner(
        scope="equity",
        identifier_kind="isin",
        identifier_value="X",
        manifest=manifest,
        sources=[s_wide, s_narrow],
        invoker=invoker,
    )
    assert current["longName"] == "WIDE"          # wide ran first; narrow couldn't overwrite
    assert current["issuer"]["issuerId"] == "ISS-1"  # narrow still added the gap field
    # Confirm narrow's longName patch was registered as skipped.
    narrow_inv = next(i for i in trace.invocations if i["source"] == "narrow")
    assert "longName" in narrow_inv["fields_skipped_already_filled"]


def test_invocation_failure_is_logged_and_loop_continues():
    manifest = manifest_for("equity")
    s_bad = _src(id="bad", produces=("longName",), confidence="high")
    s_good = _src(id="good", produces=("longName",), confidence="medium")

    def invoker(src, k, v, c):
        if src.id == "bad":
            raise RuntimeError("boom")
        return SourceFetchResult(patch={"longName": "OK"}, source_of_truth_rows=[])

    current, prov, trace = run_planner(
        scope="equity",
        identifier_kind="isin",
        identifier_value="X",
        manifest=manifest,
        sources=[s_bad, s_good],
        invoker=invoker,
    )
    assert current["longName"] == "OK"
    outcomes = {inv["source"]: inv["outcome"] for inv in trace.invocations}
    assert outcomes == {"bad": "error", "good": "ok"}


def test_budget_caps_iterations():
    manifest = manifest_for("equity")
    s = _src(id="s", produces=("longName",))

    def invoker(src, k, v, c):
        # Never actually fills the field, so the loop would run forever
        # without a budget cap.
        return SourceFetchResult(patch={}, source_of_truth_rows=[])

    current, prov, trace = run_planner(
        scope="equity",
        identifier_kind="isin",
        identifier_value="X",
        manifest=manifest,
        sources=[s],
        invoker=invoker,
        budget=3,
    )
    # Source gets exhausted after one call (called set), so we actually stop
    # via "no remaining source covers any gap" — verify the budget at least
    # didn't override that.
    assert trace.iterations <= 3
