# Agent-Ready Issue Template

Use this template when drafting or rewriting repository issues for agent-driven
implementation. Keep only sections that help the next agent make correct
decisions.

## Title

`<Action verb> <specific durable outcome>`

Examples:

- `Implement ADR-015 internal Grafana service telemetry dashboards`
- `Add Playwright UI tests for Config Registry Backoffice`
- `Rebaseline Config Registry PostgreSQL schema to surrogate UUID ids`

## Body

````markdown
## Goal

<What should change, why it matters, and who benefits. Include linked ADRs,
issues, PRs, incidents, or user requests.>

Blocked by: <issue/PR/decision, or "none">.

## Scope

- <Deliverable or behavior in scope.>
- <Path, module, or interface in scope.>
- <Tests, docs, contracts, or C4 updates in scope.>

## Out Of Scope / Non-goals

- <Explicitly excluded behavior.>
- <Follow-up work that should not be implemented in this issue.>
- <Stable identifiers or contracts that must not be renamed.>

## Affected Modules And Source Of Truth

- Module: `<module id from docs/agents/module-map.yaml>`
- Write paths:
  - `<path>`
- Source of truth:
  - `<contract, C4, ADR, docs, README, or package guide>`
- Compatibility guardrails:
  - `<stable package/topic/table/service/contract names to preserve>`

## Agent Instructions

1. Read `AGENTS.md`, `docs/agents/module-map.yaml`, and closest scoped
   `AGENTS.md` files before editing.
2. After reading the task, select the minimal applicable skills from repo-local
   `.agents/skills` and available system/session skills. Announce the selected
   skills and why; if no additional skill applies, say "additional skills: not
   applicable".
3. Before implementation, create a visible task plan from the phases below so
   it appears in the Codex side panel. Keep one step `in_progress` and update
   statuses after each phase, validation failure, or scope change.
4. Ask the user only for blocking decisions that cannot be resolved from repo
   source of truth. Prefer 1-3 concise questions with a default assumption for
   each, and record answers in the issue or PR context.
5. Read these task-specific files:
   - `<path or URL>`
6. Use these skills/workflows when relevant:
   - `<skill name and why>`
7. Do not:
   - `<important boundary>`
8. If `<condition or blocker>` appears, stop and ask for confirmation before
   implementation.

## Implementation Plan

### Phase 0: Baseline and readiness

- <Confirm blockers, source-of-truth docs, current tests, data shape, or local
  stack state.>

Validation:

- `<command>`

### Phase 1: <Implementation increment>

- <Smallest meaningful implementation step.>
- <Expected tests or assertions.>

### Phase 2: Tests, docs, contracts, and validation

- <Next scoped step.>
- <Update docs, contracts, LikeC4, ADR/decision records, package READMEs, or
  operational guides affected by the implementation. If none are affected,
  record why they are intentionally unchanged.>
- <Validation work.>

## Acceptance Criteria

- <Observable criterion with clear expected result.>
- <Criterion that maps to a test, static check, or manual validation.>
- <Docs/contracts/LikeC4/ADR/README/runbooks updated, or explicitly not needed
  with rationale.>
- <No forbidden scope or compatibility change happened.>

## Open Questions

- <Blocking question, default assumption, owner, or "none".>

## Validation

Run:

```bash
<exact command>
<exact command>
```

If a command cannot be run, record why in the PR and issue status comment.

## Completion Comment

When implementation is complete, comment with:

- PR: `<link>`
- Delivered scope: `<summary>`
- Acceptance criteria/test mapping: `<summary>`
- Validation passed: `<commands/results>`
- Docs/contracts/LikeC4/ADR/README/runbooks: `<updated or intentionally unchanged with rationale>`
- Residual risks/follow-ups: `<risks or none>`
````

## Sizing Rules

- One issue should fit one branch, one PR, and one coherent validation story.
- Split the work when it requires both a decision/ADR and implementation, or
  when production migrations/read models/hardening are separable follow-ups.
- Prefer a narrow first increment with explicit follow-up issues over a broad
  issue whose acceptance criteria cannot be completed safely.
