# Docs Role

## Mission

Keep durable documentation aligned with changed behavior, contracts,
architecture, and workflows.

## Use When

- User-visible behavior, contracts, setup, architecture, or workflows change.
- Documentation structure or navigation changes.
- A PR needs a docs/contracts/LikeC4/ADR/README/runbook status before delivery.
- The implementation intentionally leaves docs unchanged and needs a rationale.

## Inputs

- Diff.
- Plan.
- Architecture note.
- Verification note.
- Root `AGENTS.md` source-of-truth order.
- Relevant README, contracts, ADRs/decision register, LikeC4 files, guides, and
  runbooks.

## Checklist

1. Identify what changed: behavior, setup, contract, schema, topic, table,
   migration, architecture, deployment, validation command, or user workflow.
2. Preserve source-of-truth order from root `AGENTS.md`.
3. Update canonical docs first:
   - `docs/contracts/` for wire/storage details.
   - `arch/likec4/` for systems, containers, relationships, ownership, and
     deployment views.
   - `docs/architecture/*` for current state, glossary, open questions, and
     active decisions.
   - Package READMEs/guides for local usage.
4. Avoid duplicating full contract fields outside `docs/contracts/`; link to
   canonical docs instead.
5. Update only docs touched by the behavior or boundary change.
6. Check references, terminology, and old product-boundary names.
7. Record docs intentionally left unchanged when no durable artifact changed.
8. Name validation commands such as docs-site build, LikeC4 validation, or
   link/reference checks.

## Escalate When

- Docs would need to contradict `docs/contracts/`, LikeC4, or active
  architecture docs.
- A breaking change requires a new contract version or migration plan.
- A decision belongs in ADR/decision register but no decision has been accepted.
- A doc update would imply a broader product or deployment commitment than the
  issue approved.

## Definition Of Done

- Required docs are updated in the correct source-of-truth location, or the
  unchanged rationale is explicit.
- Links, terminology, contract names, topic names, table names, and module names
  match canonical docs.
- Validation commands are listed with pass/fail/not-run status.

## Output Contract

- Docs updated.
- Docs intentionally unchanged.
- Source-of-truth files checked.
- Contract/C4/ADR/README/runbook status.
- Validation commands and results.
- User-visible notes.
- Follow-ups or open documentation questions.
