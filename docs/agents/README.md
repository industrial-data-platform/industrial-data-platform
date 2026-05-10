# Agent Workspace Guide

This directory contains tracked handoff material for AI agents. It complements
the root `AGENTS.md` and should stay short enough to be useful in a fresh clone.

## Start Here

1. Read the root `AGENTS.md`.
2. Read the nearest scoped `AGENTS.md` for the files you will touch.
3. Open `module-map.yaml` to identify the owner, source of truth, and validation
   commands.
4. For large tasks, use `workflows/task-flow.md` and the role prompts
   in `roles/`.

## What Belongs Here

- Stable workflow and handoff instructions.
- Role prompts that can be reused by any agent.
- Templates for task planning, implementation notes, reviews, verification, and
  status updates.
- A machine-readable module map.

## What Does Not Belong Here

- Local task scratchpads.
- Customer secrets or credentials.
- Generated outputs from one agent run.
- Raw issue tracker exports.

Use `.local/agent-runs/` for local scratch work. `.local/` is intentionally
ignored by git.

## References

This structure follows common agent-context practices:

- root repository instructions for Codex-style agents
- short compatibility bridge files for tools with their own instruction names
- scoped instructions close to owned code
- a machine-readable module map for ownership and validation
- workflow and handoff templates for long-running tasks

## Documentation Shape

Follow the Diataxis split when writing durable documentation:

- Tutorials teach a workflow.
- How-to guides solve a specific task.
- Reference documents define exact behavior and fields.
- Explanation documents capture concepts, trade-offs, and rationale.
