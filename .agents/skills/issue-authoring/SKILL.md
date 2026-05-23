---
name: issue-authoring
description: >
  MUST USE for creating, drafting, refining, readiness-reviewing, or adapting
  GitHub issues for agent-driven work in this repository before generic Git or
  GitHub skills. Use when the desired output is an issue body, issue template,
  issue readiness review, issue rewrite, or agent-ready task specification. Key
  triggers: create/write/draft/refine an issue, prepare an issue template, adapt
  an issue for agents, make an agent-ready issue, review issue readiness,
  split/scope an issue, define acceptance criteria, "создай issue",
  "адаптируй issue под агента", "сделай шаблон issue", "подготовь задачу для
  агента", "составь issue", or similar. Inspect current open/closed issue style
  when useful, resolve repo context, draft a self-contained issue with
  ready/done gates, validation, skill selection, visible-plan expectations, and
  docs/contracts/C4/ADR completion requirements. Do not use when the user asks
  to implement, take, fix, or work on an existing issue; use issue-workflow for
  that. Do not use for general GitHub issue summaries; use github:github.
---

# Issue Authoring

Use this skill when a user asks to create, draft, rewrite, readiness-review, or
adapt an issue for agents in this repository.

Use `issue-workflow` instead when an issue already exists and the user asks to
implement, take, fix, or work on it.

## Trigger Data

Use this skill when the user intent matches one of these patterns:

- Create a new GitHub issue or local issue draft.
- Rewrite an existing rough task into an agent-ready issue.
- Add or improve acceptance criteria, validation, open questions, blockers, or
  implementation phases in an issue.
- Create or refine `.github/ISSUE_TEMPLATE/*`.
- Review whether an issue is ready for an agent before implementation.
- Split a broad task into issue-sized units.

Do not use this skill when:

- The user provides an issue number or URL and asks to implement, take, fix, or
  work on it. Use `issue-workflow`.
- The user asks for general issue/PR summaries, labels, comments, or repository
  triage without drafting an agent-ready issue. Use `github:github`.
- The user asks to address PR review comments, fix CI, or publish local changes.
  Use the corresponding GitHub plugin skill.

## Read First

1. `AGENTS.md`
2. `docs/agents/module-map.yaml`
3. The closest scoped `AGENTS.md` for likely affected paths
4. `docs/agents/workflows/task-flow.md`
5. Relevant role prompts when useful:
   - `docs/agents/roles/planner.md`
   - `docs/agents/roles/architect.md`
   - `docs/agents/roles/docs.md`
   - `docs/agents/roles/reviewer.md`
   - `docs/agents/roles/verifier.md`

## Observed Repository Issue Pattern

Recent open and closed issues in this repository are most useful to agents when
they include:

- Goal, scope, out of scope, and acceptance criteria.
- Affected modules, write paths, source-of-truth docs, and validation commands.
- Agent instructions that name required repo skills, docs, compatibility
  guardrails, and "do not do" boundaries.
- Dependencies and blockers, especially ADRs, linked issues, and required
  external docs checks.
- Implementation phases that start with baseline/readiness checks and end with
  validation and status comments.
- Completion comments that link PRs, summarize delivered scope, list validation
  evidence, and name residual risks.

## Question Policy

- Ask the user only for decisions that block a correct issue: scope boundary,
  source-of-truth conflict, breaking compatibility approval, missing acceptance
  criteria, unclear ownership, or destructive/migration behavior.
- Prefer one concise batch of questions over a long interview. Use 1-3
  questions unless the task is genuinely not ready.
- For each question, include the default assumption you would use if the user
  wants you to proceed.
- Do not ask about details that can be discovered from `AGENTS.md`,
  `docs/agents/module-map.yaml`, scoped `AGENTS.md`, contracts, C4, or existing
  issues.
- Record answered questions in the issue body, an issue comment, or the final
  draft so future agents do not rely on chat-only context.

## Workflow

1. Inspect current issue style when useful.
   - Prefer the GitHub app or `gh issue list` / `gh issue view`.
   - Compare at least one open issue and recent closed issues when the user asks
     to align with repository practice.
   - Capture recurring labels, issue size, validation style, completion comment
     style, and how blockers or linked PRs are recorded.

2. Resolve repository context before drafting.
   - Read `AGENTS.md`, `docs/agents/module-map.yaml`, and relevant scoped
     `AGENTS.md` files for likely paths.
   - Identify affected modules, write paths, source-of-truth docs, architecture
     model files, contracts, and compatibility identifiers before writing
     requirements.
   - If the work touches contracts, ClickHouse, Kafka, MQTT, C4, ADRs, runtime
     modules, or deployment topology, name the specialist skill to use.

3. Ask blocking questions before drafting when needed.
   - If the request is not ready, ask only the questions required to make the
     issue safe for an agent.
   - If reasonable defaults are safe, state them and proceed with the draft.
   - Put unresolved questions in an `Open Questions` or blocker section instead
     of hiding ambiguity in acceptance criteria.

4. Draft from the template.
   - Use `references/agent-ready-issue-template.md` when the user asks for a
     new issue, a template, or an agent-adapted rewrite.
   - Keep the issue self-contained enough that a new agent can start without
     relying on chat history.
   - Make the implementation phases short and concrete enough to translate into
     a visible task plan in the Codex side panel.
   - Prefer concrete paths, commands, table/topic names, issue links, and
     module ids over vague nouns.
   - Use the language of the requester or the existing issue, but keep section
     headings consistent enough for agents to scan.

5. Define readiness.
   - Make the Definition of Ready explicit through goal, scope, out of scope,
     affected modules, source-of-truth docs, acceptance criteria, and required
     validation.
   - Mark blockers such as "blocked by PR #N", "requires ADR acceptance", or
     "requires migration approval" near the top.
   - If a breaking compatibility change is requested, require a migration plan
     and explicit approval before implementation.

6. Define done.
   - Acceptance criteria must be observable and testable.
   - Map validation commands to affected modules from
     `docs/agents/module-map.yaml`.
   - Require the future executor to select applicable repo-local and
     system/session skills after reading the task.
   - Require a visible task plan in the Codex side panel before implementation.
   - Include post-implementation documentation expectations for docs,
     contracts, LikeC4, ADR/decision records, package READMEs, and operational
     guides. If no durable artifact needs updating, require an explicit
     "intentionally unchanged" rationale.
   - Include a completion comment expectation: delivered scope, validation,
     docs/contracts/LikeC4/ADR status, PR link, and residual risks.

7. Keep the issue sized for agent execution.
   - Split broad epics into dependency-linked issues when a single branch cannot
     safely finish implementation, tests, docs, and validation.
   - Put production hardening, richer seed data, migrations, or tenant-facing
     surfaces into follow-up issues unless they are required for the current
     acceptance criteria.

8. Create or update the issue only when intent is clear.
   - If the user asks for a draft, return title and body without creating it.
   - If the user asks to create/update the GitHub issue, restate the target
     repository and issue title/body summary before applying the write unless
     they explicitly asked for immediate creation.

## Agent-Ready Issue Checklist

- Title starts with an action and names the durable outcome.
- Goal states why the work exists in one or two paragraphs.
- Scope and out of scope are separate.
- Affected modules and write paths match `docs/agents/module-map.yaml`.
- Source-of-truth docs are named in precedence order when relevant.
- Agent instructions include required skills, blockers, compatibility guardrails,
  and explicit non-goals.
- Acceptance criteria are checkable and avoid hidden "and everything works"
  requirements.
- Implementation phases can be copied into a visible task plan with 3-7
  concrete steps.
- Validation commands are exact and runnable from the repository root unless
  stated otherwise.
- Docs, contracts, and LikeC4 expectations are explicit.
- Status comment format is clear enough to close the loop after implementation.

## Output

- Issue title.
- Issue body or changed sections.
- Affected modules and source-of-truth docs used.
- Recommended repo-local and system/session skills for the future executor.
- Required validation commands.
- Docs/contracts/LikeC4/ADR completion expectations.
- Open questions or blockers.
