# Architecture Docs Guide

Scope: `docs/architecture/`.

This directory captures current state, accepted decisions, glossary, open
questions, and explanatory architecture notes.

## Do

- Keep ADRs decision-focused and date-stamped.
- Update `current-state.md` when the working snapshot changes.
- Update `glossary.md` when terminology changes.
- Update `open-questions.md` when a decision is made or a new blocker appears.
- Keep LikeC4 in `arch/likec4/` as the diagram source of truth.

## Do Not

- Do not duplicate full contract field definitions here.
- Do not silently contradict accepted ADRs; add a new ADR or an explicit note.
- Do not use `Monitoring & Alarm Platform` as the current central system name.

## Validation

- Docs-only: `git diff --check`
- If architecture model changes too: `cd arch && npm run validate`
