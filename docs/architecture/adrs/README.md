# Architecture Decision Records

Дата: 2026-05-19
Статус: working index

ADRs are no longer default source-of-truth for current system behavior.
`decisions.md` and living docs remain the active navigation layer.

Draft/proposed ADRs may live next to this README while the team is still
discussing a significant trade-off. They are not accepted decisions until
`decisions.md` contains a matching accepted entry.

Accepted historical ADRs are kept in `archive/` as rationale: why a decision
was made, which alternatives were rejected, and what trade-offs were accepted at
the time.

## Accepted ADRs in current review

- [`ADR-016: Asset Graph Registry boundary`](ADR-016-asset-graph-registry-boundary.md)

## Superseded discussion material

- [`ADR-015: Hierarchical Catalog and Asset Graph boundary comparison`](ADR-015-hierarchical-catalog-runtime-boundary.md)

## Draft / Proposed ADRs

None at the moment.

For active architecture navigation, start with
[`../decisions.md`](../decisions.md), then use:

- [`../current-state.md`](../current-state.md) for the working system snapshot.
- [`../glossary.md`](../glossary.md) for terminology.
- [`../../contracts/README.md`](../../contracts/README.md) for contract details.
- [`../../../arch/README.md`](../../../arch/README.md) for LikeC4 model entrypoints.

Historical ADR files live in [`archive/`](archive/). If an archived ADR
disagrees with `docs/contracts/`, the contract document wins.
