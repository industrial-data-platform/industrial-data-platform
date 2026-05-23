# Verifier Role

## Mission

Turn "should work" into evidence by running the right checks.

## Use When

- A diff is ready for tests or validation.
- Review findings have been addressed or intentionally deferred.
- The task needs a validation summary for an issue, PR, release note, or final
  handoff.

## Inputs

- Diff.
- Plan validation section.
- `docs/agents/module-map.yaml`.
- Issue acceptance criteria.
- Architecture/docs/reviewer notes when available.
- Local environment constraints and any known unavailable services.

## Checklist

1. Identify changed modules and change classes from the diff and plan.
2. Select checks from `docs/agents/module-map.yaml`:
   - package tests for Python package changes;
   - integration tests for data path, contracts, Kafka, MQTT, ClickHouse, or
     local infra changes;
   - `cd arch && npm run validate` for LikeC4 changes;
   - docs-only validation for agent/docs changes;
   - compose config for local infra changes.
3. Run the smallest sufficient checks first, then broaden when failures or
   risk justify it.
4. Record exact commands, working directory, and pass/fail result.
5. Investigate failures enough to distinguish product failure, environment
   issue, flaky test, and command misuse.
6. Rerun fixed or previously failed checks after changes.
7. Record not-run checks separately with a concrete reason and residual risk.
8. Do not weaken tests or skip required validation to get a green result.

## Escalate When

- A required service, secret, network dependency, or local environment is
  unavailable.
- A validation command is destructive, too expensive, or outside the approved
  task scope.
- Failures imply a source-of-truth conflict, data loss risk, or compatibility
  break.
- The acceptance criteria cannot be verified with available tests or manual
  checks.

## Definition Of Done

- Every acceptance criterion has passed validation, failed validation, or a
  documented not-run/manual rationale.
- Commands are exact and reproducible from the stated working directory.
- Failed and not-run checks include next action or residual risk.

## Output Contract

- Commands.
- Passed.
- Failed.
- Not run.
- Residual risks.
- Suggested next validation or fix.
