"""Agentic adapter that invokes the find-and-parse-factsheet Claude skill.

The cache-fill counterpart to `fund_factsheet_patch`:

  cost-first ordering = file_read=0 → … → llm_skill=3
  fund_factsheet_patch  (file_read)  ← reads existing patch file
  fund_factsheet_skill  (llm_skill)  ← invokes the skill to write a patch

The patch source runs first; if it finds nothing, this source runs the
skill via the Claude Agent SDK, which writes the patch JSON to disk,
then we re-use the patch source's projection to return the result.

Guard conditions — the source returns None (skipped) when:
  - ANTHROPIC_API_KEY is unset
  - `claude-agent-sdk` isn't installed
  - the patch already exists on disk
  - the skill ran but didn't produce a patch file
  - any exception bubbles up from the SDK

LLM-skill sources are opt-in. `assemble_golden` defaults `max_cost_class`
to "web_fetch" so this source is filtered out unless the caller asks for
deeper enrichment (the assemble endpoint's `invoke_llm_skills=true`).
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pipeline.agentic.merger import SourceFetchResult
from pipeline.agentic.sources import fund_factsheet_patch

log = logging.getLogger(__name__)

# Surface the SDK lazily so the source module imports cleanly without the
# optional dependency installed (tests + minimal deployments).
try:  # pragma: no cover — import availability is environment-dependent
    from claude_agent_sdk import ClaudeAgentOptions, query as _sdk_query
    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    ClaudeAgentOptions = None  # type: ignore
    _sdk_query = None  # type: ignore
    _SDK_AVAILABLE = False


def fetch(
    identifier_kind: str,
    identifier_value: str,
    current: Dict[str, Any],
) -> Optional[SourceFetchResult]:
    if identifier_kind != "isin":
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.debug("fund_factsheet_skill skipped: ANTHROPIC_API_KEY unset")
        return None
    if not _SDK_AVAILABLE:
        log.debug("fund_factsheet_skill skipped: claude-agent-sdk not installed")
        return None

    patch_file = fund_factsheet_patch._patch_path_for_isin(identifier_value)
    if patch_file.exists():
        # The patch source already covered this ISIN — don't duplicate work.
        return None

    try:
        asyncio.run(_invoke_skill(identifier_value, current))
    except Exception as exc:  # noqa: BLE001 — SDK errors vary
        log.warning("find-and-parse-factsheet skill failed for %s: %s", identifier_value, exc)
        return None

    if not patch_file.exists():
        log.info("skill ran but no patch produced for %s", identifier_value)
        return None

    # Reuse the patch source's projection — same file, same provenance shape.
    return fund_factsheet_patch.fetch(identifier_kind, identifier_value, current)


async def _invoke_skill(isin: str, current: Dict[str, Any]) -> None:
    """Run the find-and-parse-factsheet skill via the Claude Agent SDK."""
    long_name = current.get("longName") or "(unknown)"
    umbrella_name = (current.get("umbrella") or {}).get("legalName") or "(unknown)"
    mgmt_name = (current.get("managementCompany") or {}).get("legalName") or "(unknown)"

    prompt = (
        f"Invoke the find-and-parse-factsheet skill for the fund with ISIN {isin}.\n"
        f"Already known (from FIRDS): long name = {long_name!r}, "
        f"umbrella = {umbrella_name!r}, management company = {mgmt_name!r}.\n"
        f"Write the patch JSON to data/opensearch/golden/fund/patches/FG-{isin}-001.json.\n"
        f"Skip the OpenSearch PATCH step and the user-confirmation step — the "
        f"agentic platform applies the patch via its own merger after you return."
    )

    options = ClaudeAgentOptions(
        cwd=str(Path.cwd()),
        allowed_tools=["WebFetch", "WebSearch", "Read", "Write", "Bash"],
    )
    async for _message in _sdk_query(prompt=prompt, options=options):
        # We don't surface intermediate messages — the side effect (the
        # patch file on disk) is the contract.
        pass
