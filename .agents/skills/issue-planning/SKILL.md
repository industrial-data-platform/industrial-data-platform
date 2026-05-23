---
name: issue-planning
description: >
  MUST USE for creating, drafting, refining, readiness-reviewing, or adapting
  technical GitHub issues for agent-driven development in this repository
  before generic Git or GitHub skills. Use for issue bodies, templates,
  readiness reviews, rewrites, or agent-ready specs for Industrial Data
  Platform, Edge Telemetry Agent, Web Monitoring, Alarm Management, contracts,
  architecture, infra, docs, or tests. Key triggers:
  create/write/draft/refine an issue, adapt an issue for agents, split/scope an
  issue, define acceptance criteria, "создай issue", "адаптируй issue под
  агента", "сделай шаблон issue", "подготовь задачу для агента", "составь
  issue", or similar. Draft a self-contained technical execution brief with
  module impact, source-of-truth docs, validation, skill selection, visible-plan
  expectations, and docs/contracts/C4/ADR requirements. Do not use
  for issue implementation; use issue-workflow. Do not use for sales proposals,
  commercial offers, pricing, product marketing, or general GitHub summaries.
---

# Issue Planning

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

## Repository Technical Context

Treat an issue as a technical execution brief for this monorepo, not as a
generic proposal. The useful context is:

- Which system or module changes: `industrial_data_platform`,
  `edge_telemetry_agent`, `web_monitoring_module`, `alarm_management_module`,
  or `demo_and_knx_tooling`.
- Which change class applies: module implementation, docs-only, contract,
  architecture/C4, infra, tests, CI, or another cross-cutting area.
- Which technical surface changes: runtime behavior, public API, MQTT/Kafka
  contract, ClickHouse/PostgreSQL storage, edge SQLite state, config model,
  local infrastructure, Grafana/read model, LikeC4 architecture, README/docs,
  tests, or CI/validation.
- Which source of truth wins: `docs/contracts/` first for wire/storage details,
  then `arch/likec4/`, then `docs/architecture/current-state.md`,
  `glossary.md`, `open-questions.md`, `decisions.md`, and package docs.
- Which compatibility identifiers must be preserved: `idp.*`, `idp/v1`,
  stable Python package/import/entrypoint names, Docker service/image names,
  ClickHouse table/view names, migration filenames, and contract ids.
- What evidence proves done: targeted tests, integration tests, schema/contract
  validation, `cd arch && npm run validate`, docs-site build, compose config,
  or a clear "not automated" rationale.

Do not add commercial sections such as pricing, product packages, buyer proof,
discounts, offer validity, tax, VAT, or procurement terms. If business context
matters, reduce it to technical motivation and acceptance criteria.

## Technical Impact Classification

Before drafting, classify the task with this checklist:

1. Module and ownership: choose module ids and write paths from
   `docs/agents/module-map.yaml`.
2. Change class: name whether this is module implementation, docs-only,
   contract, architecture/C4, infra, tests, CI, or another cross-cutting area.
3. Current behavior and target behavior: name the existing code, contract,
   data flow, or doc state and the desired durable outcome.
4. Contract/storage impact: MQTT, Kafka, ClickHouse, PostgreSQL, edge SQLite,
   JSON schemas, migrations, producers, consumers, or no contract impact.
5. Architecture impact: LikeC4, module boundaries, deployment paths, runtime
   ownership, ADR/decision register, or "architecture unchanged".
6. Validation impact: exact commands from `module-map.yaml`, plus integration,
   docs, C4, compose, or link/reference checks.
7. Stop conditions: breaking compatibility, source-of-truth conflict, unclear
   owner, destructive migration, missing external docs decision, or user
   approval needed.

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
   - Read `docs/architecture/current-state.md` and `docs/architecture/decisions.md`
     when module boundaries, current platform state, or product direction affect
     the task.
   - Read relevant `docs/contracts/` files before drafting requirements that
     mention MQTT, Kafka, ClickHouse, edge config, edge SQLite state, schemas,
     migrations, producers, or consumers.
   - Identify affected modules, write paths, source-of-truth docs, architecture
     model files, contracts, and compatibility identifiers before writing
     requirements.
   - If the work touches contracts, ClickHouse, Kafka, MQTT, C4, ADRs, runtime
     modules, or deployment topology, name the specialist skill to use.
   - Avoid importing generic business proposal structure into technical issues.
     Keep business motivation short and translate it into observable technical
     behavior, constraints, and validation.

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
   - Include a `Technical Context / Impact` section when the task changes code,
     contracts, infrastructure, architecture, or durable docs.
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
- Cross-cutting change class is named separately from module id when the work is
  docs-only, C4-only, CI, infra, or validation-only.
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
- Technical impact classification, change class, and stop conditions.
- Recommended repo-local and system/session skills for the future executor.
- Required validation commands.
- Docs/contracts/LikeC4/ADR completion expectations.
- Open questions or blockers.
