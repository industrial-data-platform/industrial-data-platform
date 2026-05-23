---
name: issue-workflow
description: >
  MUST USE for implementing, taking, fixing, or preparing an existing GitHub
  issue in this repository before generic Git or GitHub skills. Trigger when
  the user asks to implement/work on/fix/take an issue from a URL, issue link,
  or issue number, including GitHub issue URLs, "implement issue", "work on
  issue #123", "реализуй issue", "сделай реализацию issue", "возьми задачу",
  "возьми тикет", "почини issue", "сделай задачу #123", or similar. Use when
  the desired output is code/docs/tests/PR/status based on an existing issue.
  Read the issue, select applicable repo-local and system/session skills,
  define ready/done gates, maintain a visible task plan, branch safely,
  implement with TDD, validate, reconcile docs/contracts/C4/ADR, and prepare
  issue or PR status. Do not use for creating, drafting, refining, or adapting
  issues for agents; use issue-planning for that. Do not use for general
  GitHub issue summaries; use github:github.
---

# Issue Workflow

Use this skill when a user asks to work from an existing issue link, GitHub
issue URL, issue number, or issue-driven implementation task.

Use `issue-planning` instead when the user asks to create, draft, rewrite,
readiness-review, or adapt an issue for agents.

## Trigger Data

Use this skill when the user intent matches one of these patterns:

- Implement an existing GitHub issue from a URL, number, or issue reference.
- Take an issue into work, prepare its branch, or continue issue-driven work.
- Fix an issue or bug described by an existing issue.
- Evaluate readiness only as the first step before coding that issue.
- Produce implementation status, validation evidence, PR body, or issue comment
  after working on the issue.

Do not use this skill when:

- The user wants to create, draft, rewrite, template, split, or adapt an issue
  for a future agent. Use `issue-planning`.
- The user only wants a repository/issue/PR summary or labels/comments triage.
  Use `github:github`.
- The user wants to address PR review comments, debug CI, or publish already
  completed local changes. Use the corresponding GitHub plugin skill.

## Read First

1. `AGENTS.md`
2. `docs/agents/module-map.yaml`
3. The closest scoped `AGENTS.md` for affected paths
4. `docs/agents/workflows/task-flow.md`
5. Relevant architecture model files under `arch/likec4/`, selected by the
   affected module in `docs/agents/module-map.yaml`
6. Relevant role prompts:
   - `docs/agents/roles/architect.md`
   - `docs/agents/roles/docs.md`
   - `docs/agents/roles/reviewer.md`
   - `docs/agents/roles/verifier.md`

## Workflow

1. Read the GitHub issue.
   - Prefer the GitHub app or `gh issue view`.
   - Capture title, body, labels, linked PRs, comments, acceptance criteria,
     affected modules, and any attached logs or screenshots.
   - Check logs, screenshots, and pasted config for secrets or sensitive data;
     do not copy secrets into commits, docs, PRs, or issue comments.
   - If the issue cannot be read, ask the user for the issue URL or content.

2. Review readiness before coding.
   - Use the architect role to check boundaries, contracts, C4, deployment,
     ADR impact, module ownership, and compatibility identifiers.
   - Make a short technical impact pass:
     module id, write paths, current behavior, target behavior, contract/storage
     impact, architecture impact, docs impact, validation commands, and stop
     conditions.
   - Use existing LikeC4 model context as architecture input, especially
     systems, containers, relationships, deployment views, and ownership
     boundaries for the affected module.
   - Read `docs/architecture/current-state.md` and
     `docs/architecture/decisions.md` when the task touches module boundaries,
     current platform state, pilot direction, or accepted architectural
     decisions.
   - Read relevant `docs/contracts/` files before changing MQTT, Kafka,
     ClickHouse, edge config, edge SQLite state, schemas, migrations, producers,
     or consumers.
   - Use the docs role to check whether README, contracts, C4, ADRs, guides,
     or user-facing notes will need updates.
   - Use the reviewer role to identify likely regressions, missing acceptance
     criteria, missing tests, and risky assumptions.
   - If the issue conflicts with `docs/contracts/`, `arch/likec4/`, or
     `docs/architecture/`, flag the conflict and do not silently choose the
     issue over the repository source of truth.
   - If the issue implies a breaking contract, ClickHouse, Kafka, MQTT, Docker,
     package, entrypoint, or compatibility identifier change, stop and ask for
     an explicit migration plan or user approval.
   - Use delegated subagents only when the active environment allows it and the
     user explicitly asked for delegation or parallel agent work.

3. Select the task skills.
   - After reading the task and before implementation, choose the minimal set
     of applicable skills from this repository's `.agents/skills` and from the
     available system/session skills.
   - Prefer repo-local skills for repository-specific rules:
     `issue-workflow`, `industrial-data-contracts`, and
     `platform-architecture-change`.
   - Use `industrial-data-contracts` when the technical impact pass includes
     MQTT, Kafka, ClickHouse, edge config, edge SQLite state, schemas,
     migrations, producers, consumers, or contract tests.
   - Use `platform-architecture-change` when the impact pass includes LikeC4,
     module boundaries, ownership, deployment views, ADRs, or a new runtime
     package.
   - Add system/session skills for general specialist work such as external
     library docs (`context7`), Python architecture/testing, LikeC4 syntax,
     frontend/browser verification, security scans, GitHub workflows, or
     document/spreadsheet/presentation artifacts.
   - Announce the selected skills and why in a short working update before
     using them.
   - If no additional skill applies, explicitly say "additional skills: not
     applicable" and continue.
   - Do not keep using a skill after scope changes make it irrelevant; update
     the visible plan and working notes when the skill set changes.

4. Define ready and done.
   - Definition of Ready: goal, scope, out of scope, acceptance criteria,
     affected modules, write scope, architecture/contract/docs impact, and
     required validation are clear.
   - Definition of Done: implementation is complete, each acceptance criterion
     maps to a test or validation result, required docs/contracts/LikeC4/ADR
     updates are complete or intentionally skipped, and validation evidence is
     recorded.
   - Do not start implementation until blockers in Definition of Ready are
     resolved or explicitly accepted by the user.

5. Create and maintain the visible task plan.
   - Before implementation, create a concise visible plan from the issue phases
     so it appears in the Codex side panel when the environment supports it.
   - Use 3-7 steps, usually readiness, branch setup, tests, implementation,
     docs/contracts reconciliation, validation, and PR/status.
   - Keep at most one step `in_progress`.
   - Update the plan after each completed phase, after validation failures, and
     whenever scope or acceptance criteria change.
   - The visible plan does not replace the issue. Sync durable scope changes
     back to the issue body, an issue comment, or the PR summary.

6. Ask clarifying questions when the issue is not ready.
   - Ask only the questions that block a correct implementation.
   - Prefer one concise batch of 1-3 questions and include the default
     assumption you would use if the user wants you to proceed.
   - Do not ask about details that can be discovered from repository source of
     truth, existing tests, contracts, C4, or current issue comments.
   - Do not implement against ambiguous acceptance criteria, unclear ownership,
     or conflicting source-of-truth documents.
   - When answers change scope or acceptance criteria, propose that the user
     record the clarified requirements in the issue, issue comment, or local
     plan before implementation continues.
   - If the user approves a default assumption, update the visible plan and
     include the assumption in the PR/issue status.

7. Prepare the branch safely.
   - Check `git status --short` first and do not overwrite unrelated work.
   - If the current branch has uncommitted changes, stop before switching and
     offer the user clear options:
     - commit the current changes first;
     - stash the current changes;
     - create a separate branch for the current changes;
     - keep working on the current branch if it is already the intended issue
       branch;
     - cancel or postpone the issue work.
   - Do not choose one of these options, auto-stash, reset, or move user changes
     without explicit user confirmation.
   - Do not run destructive commands or auto-stash user changes unless the user
     explicitly approves that action.
   - Before creating any new branch, check whether the current branch, a local
     branch, a remote branch, or an open PR already references the issue number.
   - If an existing branch/PR is clearly the intended issue work branch, reuse
     it. Switch to it only after dirty-state handling, update it with
     `git pull --ff-only` when it tracks a remote, and continue there.
   - If the current clean branch is already the intended issue branch, keep
     working there and do not switch to mainline just to recreate it.
   - If no suitable issue branch exists, determine the mainline branch from the
     repository context, usually `main`, `master`, or `origin/HEAD`.
   - For a new issue branch, switch to the mainline branch and pull the latest
     changes with a fast-forward-only update: `git switch <mainline>` then
     `git pull --ff-only`.
   - Create the fresh issue branch from the updated mainline branch using:
     `codex/issue/<issue-number>-<short-slug>`.
   - If the user or repository policy requires another branch prefix, keep the
     `/issue/<issue-number>-<short-slug>` segment in the branch name.
   - Do not implement issue changes on the mainline branch.

8. Implement with TDD.
   - Map each acceptance criterion to a failing test, existing test, manual
     validation command, or explicit "not automated" rationale.
   - When using, installing, upgrading, or debugging any external library,
     framework, or service API, use the `context7` skill first to fetch current
     documentation instead of relying on memory.
   - Record the library id/query or docs source checked when it affects an
     implementation choice.
   - For behavior or code changes, add or update the smallest useful failing
     test first.
   - For docs-only, C4-only, ADR-only, template-only, or validation-only work,
     establish the relevant baseline validation first instead of inventing an
     artificial failing unit test.
   - For contract, schema, storage, or migration changes, add or update a
     contract fixture, schema check, migration assertion, or integration test
     before implementation when feasible.
   - Run the targeted test or baseline validation and confirm it fails or
     exposes the expected gap when a failing check is appropriate.
   - Implement the minimal scoped change.
   - Rerun the targeted test until it passes.
   - For Python implementation work, use the `python-clean-architecture` skill.
   - For Python tests, prefer the repository pytest patterns and use the
     `python-testing` skill when test structure or fixtures are non-trivial.

9. Validate.
   - Run validation from `docs/agents/module-map.yaml` for affected modules.
   - Run lint checks when code changed.
   - Run integration tests when data paths, contracts, local infra, Kafka,
     MQTT, ClickHouse, or cross-module behavior changed.
   - If docs, contracts, or C4 changed, run their required validation too.

10. Fix validation results.
   - Investigate failures instead of weakening tests.
   - Fix the implementation, tests, docs, or contracts as needed.
   - Rerun the failed checks and any nearby checks that could be affected.

11. Self-review before delivery.
   - Check for scope creep, accidental compatibility changes, unnecessary
     abstractions, missing tests, docs drift, and LikeC4 drift.
   - Reconcile the implementation against Definition of Done before preparing
     final status.

12. Reconcile documentation and contracts before completion.
   - Before marking the issue done, re-check whether the completed task changed
     behavior, setup, contracts, public interfaces, architecture, operational
     workflows, validation commands, or user-visible usage.
   - Update durable docs, `docs/contracts/`, LikeC4, ADR/decision records,
     package READMEs, implementation guides, and runbooks when they are affected.
   - Update `arch/likec4/` when implementation changes durable architecture:
     module boundaries, systems, containers, relationships, dependencies,
     deployment paths, runtime ownership, or data-flow shape.
   - Use the `likec4-dsl` skill for non-trivial LikeC4 edits.
   - Preserve the source-of-truth order from `AGENTS.md`.
   - Record docs/contracts/LikeC4 intentionally unchanged in the PR and issue
     status comment when no durable update is required.

13. Publish after implementation when requested.
   - After implementation, required docs/LikeC4 updates, self-review, and
     successful validation, commit the completed work when the user asked for a
     commit/push/PR, the issue workflow explicitly requires publication, or the
     user confirms publication after validation.
   - Stage only files that belong to the issue; never include unrelated dirty
     worktree changes.
   - Use a concise commit message that references the issue number.
   - Push the issue branch only when publication is requested or confirmed.
   - Create or update a PR that links the issue when the user asks for a PR or
     repository workflow requires one.
   - When creating or updating a PR, the PR body must include implementation
     summary, acceptance criteria/test mapping, validation results,
     docs/contracts/LikeC4/ADR note, and residual risks.
   - If validation is blocked or failing, do not present the PR as ready; create
     a draft PR only when the user wants a visible work-in-progress.
   - Prepare a concise issue comment when useful: what changed, validation
     results, docs/contracts/LikeC4/ADR status, and anything intentionally out
     of scope.

## Output

- Issue summary and readiness decision.
- Clarifying questions asked, or "none needed".
- Selected repo-local and system/session skills, or "not applicable".
- Definition of Ready and Definition of Done.
- Visible plan steps and final statuses.
- Branch name and mainline branch used.
- Implementation summary and changed paths.
- Acceptance criteria mapped to tests, validation, or rationale.
- External library docs checked with `context7`, or "not applicable".
- Documentation, contracts, LikeC4, and ADR records updated, or why they were
  not needed.
- Validation commands run, passed, failed, and not run.
- Residual risks and suggested issue/PR status.
