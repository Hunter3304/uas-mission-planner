# Hannover real-data route recovery

Approved by the user on 2026-10-08. Implementation must follow HANDOFF.md.

Tracking: Milestone 8 / Issue #79. Integration branch: `iteration/009` from
main `17d9b27`; feature: `feature/iteration009-route-recovery`.
Initial local implementation preceded tracking while normal CLI authentication
was being completed. Issue assignment preceded feature branch creation.
Part 5's separate branch and evidence are preserved; no Part 5 integration is included.

## Goal

Produce and display a real Hannover research route under explicit, traceable
assumptions, while preserving strict-mode validation. Synthetic routes are not
substitutes for real-data acceptance. Preserve original source snapshots.

## Approved scope

1. Reproduce failures for rheuma-podbi -> mhh (primary acceptance pair),
   amedes-georg -> mhh, and limbach-lehrte -> mhh. Separate input errors,
   missing data, constraint failures and search failures.
2. Inspect all 76 anomalous OSM geometry records. Repair recoverable geometry
   in a derived model with provenance. Localize uncertainty where possible.
   Strict mode retains unresolved blockers. Research mode explicitly records
   assumptions for records whose extents cannot be located; never silently
   omit these records or imply complete constraint validation.
3. Define research policies for zone applicability, temporary restrictions and
   unknown building heights. Prefer existing evidence for heights; otherwise
   expose configurable, documented estimates with their effect in the result.
   Preserve known obstacles, boundaries and terrain coverage constraints.
   Verify/convert vertical references when supported; never equate NHN with MSL.
4. Build bounded local search corridors with progressive expansion within
   retained source coverage. Validate exact endpoint connectors. Report endpoint
   conflicts and allow explicit selection of nearby launch/landing points;
   never silently move an endpoint. Establish stable A* routing first, then
   validate Dijkstra and ABIT*. Report preparation and search timings separately.
5. Provide date/time selectors with Europe/Berlin offsets and interval validation
   (positive, at most 24 hours), an existing-terrain dataset selector, actionable
   diagnostics, visible research assumptions, route display and complete exports.
6. Independently verify primary real-route endpoints, full-motion coverage,
   known-obstacle avoidance, cost and cruise estimates. Evaluate both additional
   pairs and retain explicit failures. Run regression checks for strict mode,
   synthetic examples and existing UI/API behavior. Deliver real GeoJSON evidence,
   validation results and remaining data limitations; update HANDOFF.md.

## Delivery order

Resolve real-data preflight blockers and obtain the primary route before UI polish
and extended algorithm comparisons. A known unavoidable endpoint obstacle must
be addressed through an explicitly selected alternative site, not relaxed checks.

## Status

Implementation and local acceptance complete. All three real pairs have
independently checked research routes. Strict preflight remains unresolved.
See `doc/iteration/iteration-009/outcome.md` for evidence and integration status.
