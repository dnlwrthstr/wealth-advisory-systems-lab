# Project Context

## Project: frosty-nash-3a9b82
- **Created**: 2026-05-17T10:26:36.842520
- **SpecPulse Version**: 2.7.5
- **AI Assistant**: Not configured

## Active Feature: 004-lookthrough-full-list
- **ID**: 004
- **Name**: lookthrough-full-list
- **One-liner**: refine fund_lookthrough_skill predicate + add merger marker-based list-replacement so the proxy fallback enhances factsheet's top-N to the full constituent list
- **Branch**: feat/lookthrough-full-list (off main, post-PR-#9)
- **Status**: 📝 TASKS — spec-002 + plan-001 + tasks-001 drafted; awaiting /sp-execute
- **Created**: 2026-05-18T20:30:00Z
- **Spec (current)**: .specpulse/specs/004-lookthrough-full-list/spec-002.md (clarified; supersedes spec-001)
- **Spec (placeholder)**: .specpulse/specs/004-lookthrough-full-list/spec-001.md
- **Plan (current)**: .specpulse/plans/004-lookthrough-full-list/plan-001.md (6 phases, ~4h)
- **Tasks (current)**: .specpulse/tasks/004-lookthrough-full-list/tasks-001.md (9 tasks T001–T009, strict serial; ~4h)
- **Design decisions resolved upfront**:
  - Feature name: lookthrough-full-list (action-oriented)
  - Merger approach: marker-based override (`_replace` sentinel) — surgical, doesn't change semantics for other source chains
- **Live validation gap from spec-003**: factsheet skill produces a top-10 projection from Amundi's holdings page; lookthrough predicate short-circuits on "holdings already populated"; users never see the full ~1310 MSCI World constituents. This spec closes that gap.

## Completed Feature: 003-agentic-fund-universe (extension — lookthrough skill) ✅ MERGED 2026-05-18
- **ID**: 003
- **Name**: agentic-fund-universe
- **One-liner**: extend agentic fund chain with synthetic-ETF look-through via physical proxy
- **Branch**: feat/fund-lookthrough-skill (merged + deleted)
- **PRs**: #5 (universe ticker fix), #6 (main spec-003 implementation), #7 / #8 / #9 (docker-stack infrastructure for the LLM skills)
- **Status**: ✅ MERGED — 13/14 tasks done; T011b discovered factsheet skill produces top-N rather than gating empty → feature 004 closes the gap
- **Created**: 2026-05-18T15:50:00Z
- **Spec (current)**: .specpulse/specs/003-agentic-fund-universe/spec-003.md (supersedes spec-002.md)
- **Spec (prior, implemented + merged via PR #4)**: .specpulse/specs/003-agentic-fund-universe/spec-002.md
- **Plan (current)**: .specpulse/plans/003-agentic-fund-universe/plan-002.md (8 phases, ~9.5h, supersedes plan-001.md)
- **Plan (prior, executed)**: .specpulse/plans/003-agentic-fund-universe/plan-001.md
- **Tasks (current)**: .specpulse/tasks/003-agentic-fund-universe/tasks-002.md (13 tasks T001–T013, strict serial; ~9.5h)
- **Tasks (prior, completed)**: .specpulse/tasks/003-agentic-fund-universe/tasks-001.md (11/11 done)

## Completed Sub-Feature: 003-agentic-fund-universe (spec-002)
- **Branch**: feat/agentic-fund-universe (merged + deleted)
- **PR**: https://github.com/dnlwrthstr/wealth-advisory-systems-lab/pull/4
- **Spec**: .specpulse/specs/003-agentic-fund-universe/spec-002.md (DoD ticked)
- **Plan**: .specpulse/plans/003-agentic-fund-universe/plan-001.md
- **Tasks**: .specpulse/tasks/003-agentic-fund-universe/tasks-001.md (11/11)

## Previous Features

### 002-agentic-bond-universe ✅ MERGED to main 2026-05-18
- **Branch**: feat/agentic-bond-universe (deleted post-merge)
- **PR**: https://github.com/dnlwrthstr/wealth-advisory-systems-lab/pull/2
- **Spec**: .specpulse/specs/002-agentic-bond-universe/spec-002.md
- **Plan**: .specpulse/plans/002-agentic-bond-universe/plan-001.md
- **Tasks**: .specpulse/tasks/002-agentic-bond-universe/tasks-001.md (12/12 — includes T012 search-mirror fix)

### 001-agentic-equity-universe ✅ MERGED to main 2026-05-18
- **Branch**: feat/agentic-equity-universe (deleted post-merge)
- **PR**: https://github.com/dnlwrthstr/wealth-advisory-systems-lab/pull/1
- **Spec**: .specpulse/specs/001-agentic-equity-universe/spec-002.md
- **Plan**: .specpulse/plans/001-agentic-equity-universe/plan-001.md
- **Tasks**: .specpulse/tasks/001-agentic-equity-universe/tasks-001.md (17/17)

## Recent Activity
- 2026-05-18T16:50 — tasks-002.md generated via /sp-task. 13 tasks (T001–T013), strict serial chain, ~9.5h total. Each task ≤ 2h, scoped to a single phase and concrete file set. Critical path: ontology → source module → registry → per-skill plumbing → tests → live smoke → docs → UI → sign-off.
- 2026-05-18T16:35 — All 4 open questions resolved. spec-003 gains Clarifications 5–7 + AC-6b. plan-002 Phase 3 restructured to absorb per-skill control plumbing (`allowed_llm_skills` threaded through agent/assemble/planner; `--enable-llm-skills` + `--llm-skills` flag pair on the CLI; `--enable-factsheet-skill` deprecated alias). 8 phases total, ~9.5h estimated.
- 2026-05-18T16:20 — plan-002.md Phase 7 added (UI surfacing of `lookthroughProvenance` in fund detail panel + holdings table cue). 8 phases, ~9h.
- 2026-05-18T16:10 — plan-002.md generated via /sp-plan; supersedes plan-001.md. 7 phases (~8h), targets spec-003 scope (synthetic-ETF look-through via physical-equivalent proxy). New source `fund_lookthrough_skill.py`, ontology additions (`Holding.source` enum + `LookthroughProvenance` value object on FundGolden), no new requirements.txt deps.
- 2026-05-18T15:55 — spec-003.md drafted via /sp-spec; supersedes spec-002.md. Adds `fund_lookthrough_skill` (5th source) for synthetic-ETF look-through via physical-equivalent ETF proxy. Triggers only when `holdings` empty + `replicationMethod ∈ {synthetic, swap}`. Ontology gains `holdings[].source` enum and `lookthroughProvenance` block. Reuses `--enable-factsheet-skill` cost gate. All 4 design questions resolved (recommended picks across the board).
- 2026-05-18T15:50 — Branch `feat/fund-lookthrough-skill` created off main (post-PR-#4 merged HEAD `ae82269`).
- 2026-05-18 — Feature 003 (spec-002 scope) merged via PR #4; remote branch deleted. 11/11 tasks done, DoD ticked.
- 2026-05-18T11:15 — tasks-001.md generated via /sp-task (11 tasks across Phase 0–5; ~7h estimated).
- 2026-05-18T11:00 — plan-001.md generated via /sp-plan (5 phases; mirrors feature 002's plan with fund-specific LLM-cost-class control and three-LEI chain semantics).
- 2026-05-18T10:45 — spec-002.md generated via /sp-spec; all 4 open questions clarified interactively (--enable-factsheet-skill boolean, no patch pre-check, no --limit default cap, raw chain counts).
- 2026-05-18T10:30 — Feature 003-agentic-fund-universe initialized via /sp-pulse. Branch feat/agentic-fund-universe created off origin/main (which now includes features 001 + 002 merges).
- 2026-05-18 — Feature 002 merged via PR #2; remote branch deleted. Included bond-universe CLI + legacy strip + search-mirror ow_type bug fix.
- 2026-05-18T06:45 — tasks-001.md generated via /sp-task (11 tasks across Phase 0–5; ~7h estimated).
- 2026-05-18T06:30 — plan-001.md generated via /sp-plan (5 phases; reuses feature 001's layered API and search-mirror pattern; no new deps, no new helper module).
- 2026-05-18T06:15 — spec-002.md generated via /sp-spec; 4 of 5 open questions clarified interactively (single --issuer-lei, --all default, no --group, no --limit-total).
- 2026-05-18T06:00 — Feature 002-agentic-bond-universe initialized via /sp-pulse. Branch feat/agentic-bond-universe created off origin/main (which now includes feature 001's merge).
- 2026-05-18 — Feature 001 merged via PR #1; remote branch deleted.
- 2026-05-18 — Phase 5–6 complete: T013 (legacy SMI snapshot), T014 (live CLI run AC-1+AC-2 met), T015 (parity diff — no regressions, +1 data quality fix on PGHN.SW), T016 (equity_yahoo.py stripped to library), T017 (final smoke). DoD ticked.
- 2026-05-17T12:30:00Z — /sp-execute Phase 1–4 complete. T003–T012 done. 162/162 tests pass.
- 2026-05-17T11:45:00Z — /sp-execute Phase 0 complete. T001, T002 done. Plan addendum recorded; T016 scope revised (cannot delete entire equity_yahoo.py — agentic source depends on it).
- 2026-05-17T11:30:00Z — tasks-001.md generated via /sp-task (17 tasks across Phase 0–6).
- 2026-05-17T11:15:00Z — plan-001.md generated via /sp-plan (6 phases, ~16h estimated).
- 2026-05-17T11:00:00Z — spec-002.md generated via /sp-spec; 4 of 5 open questions clarified interactively.
- 2026-05-17T10:52:00Z — Feature 001-agentic-equity-universe initialized via /sp-pulse.
- 2026-05-17T10:26:36Z — Project initialized successfully.

---
*This file is automatically maintained by SpecPulse*
