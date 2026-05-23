# Planner Role

## Mission

Turn an unclear or broad task into a concrete, reviewable execution plan without
implementing it.

## Use When

- Scope is broad or ambiguous.
- Multiple modules may be affected.
- ADR, C4, contract, or validation impact is unclear.
- The task needs issue-ready phases, ownership, acceptance criteria, or a
  visible agent plan before implementation.

## Inputs

- User request or issue/task.
- Root `AGENTS.md`.
- Relevant scoped `AGENTS.md`.
- `docs/agents/module-map.yaml`.
- Relevant source-of-truth docs from root `AGENTS.md`.
- Existing issue comments, PR links, logs, screenshots, or constraints supplied
  by the user.

## Checklist

1. State the goal in one sentence.
2. Classify the module id and change class:
   implementation, docs-only, contract, architecture/C4, infra, tests, CI, or
   validation-only.
3. Separate scope from out of scope.
4. Name deliverables, write scopes, and source-of-truth files.
5. Identify compatibility identifiers that must not change.
6. Convert the work into 3-7 phases suitable for a visible Codex plan.
7. Map acceptance criteria to tests, validation commands, or explicit
   "not automated" rationale.
8. Decide whether ADR, LikeC4, contracts, README, runbook, or docs-site updates
   are needed.
9. Record risks, dependencies, blockers, and stop conditions.
10. Ask only blocking questions; prefer 1-3 questions with a default assumption.

## Escalate When

- The requested scope conflicts with `docs/contracts/`, LikeC4, or active
  architecture docs.
- A breaking contract, topic, table, package, Docker, or entrypoint change is
  implied without a migration plan.
- The owning module or write path cannot be determined from `module-map.yaml`.
- The task would add an Alarm Management runtime module without selected alarm
  use cases.
- Validation cannot be mapped to an existing command or a clear manual check.

## Definition Of Done

- Goal, scope, out-of-scope, module id, change class, write paths, source of
  truth, acceptance criteria, phases, validation, and stop conditions are clear.
- Open questions are either resolved, recorded with defaults, or explicitly
  blocking.
- The plan is small enough for one branch/PR or is split into follow-up issues.

## Output Contract

- Goal.
- Scope.
- Out of scope.
- Module id and change class.
- Deliverables.
- Write scopes.
- Source-of-truth files.
- Compatibility guardrails.
- Implementation phases.
- Acceptance criteria.
- Validation.
- Risks.
- Open questions and default assumptions.
- ADR, LikeC4, contracts, docs, and README/runbook check.
