# Role Prompt Guidelines

Use these rules for every role prompt.

## Required Shape

- Mission: why this role exists.
- Use when: when to invoke it.
- Inputs: files or context to read first.
- Checklist: ordered actions.
- Escalate when: cases where the role should stop and ask.
- Definition of Done: how the role knows it is finished.
- Output contract: exact handoff content.

## Rules

- Keep role prompts small and direct.
- Separate context, task, constraints, and expected output.
- Use existing repository documents as the source for role routines; do not
  invent a parallel process when `AGENTS.md`, `module-map.yaml`, contracts, C4,
  or task-flow already defines it.
- Read first, narrow scope, then act.
- Make each checklist item an action or decision with a visible output.
- Capture common edge cases: missing scope, source-of-truth conflict, breaking
  compatibility, dirty worktree, unavailable validation, and unclear owner.
- Prefer the simplest role handoff that can produce reliable evidence. Add
  multi-role handoffs only when the work genuinely crosses planning,
  architecture, implementation, review, verification, docs, or release.
- If a contract, architecture boundary, or write owner is unclear, escalate.
- Do not mix multiple roles in one handoff unless the task is explicitly small.
- Do not write vague output such as "looks good" without evidence.
- Do not expose private reasoning. Provide decisions, evidence, assumptions,
  open questions, and exact commands instead.

## Repository Defaults

- Source-of-truth order:
  1. `docs/contracts/`
  2. `arch/likec4/`
  3. `docs/architecture/current-state.md`, `glossary.md`,
     `open-questions.md`
  4. `docs/architecture/decisions.md`
  5. Package READMEs and local guides
- Use `docs/agents/module-map.yaml` for module ownership, write paths, and
  validation commands.
- Keep module id separate from change class. Example change classes:
  implementation, docs-only, contract, architecture/C4, infra, tests, CI, and
  validation-only.
- Preserve compatibility identifiers from `AGENTS.md`: `idp.*`, `idp/v1`,
  package/import/entrypoint names, Docker names, ClickHouse table/view names,
  migration filenames, and contract ids.
- For every role, evidence should answer:
  - Did we preserve what must not break?
  - Did we do what the task asked?
  - Is the result good enough to hand off?

## Skills

Use specialized skills only when they reduce risk:

- Use `documentation-engineer` for docs systems and navigation.
- Use `likec4-dsl` for LikeC4 edits or reviews.
- Use `python-clean-architecture` for Python layering and dependency direction.
- Use `context7` for version-sensitive external libraries or APIs.
- Use `solution-architect` for architecture trade-offs and ADR decisions.
