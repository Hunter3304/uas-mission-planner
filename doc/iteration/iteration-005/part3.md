# Iteration 005 Part 3 — Constrained shortest-route demo

User authorized completion on 2026-09-30. Issue #51 belongs to Milestone #5;
its feature branch follows the existing iteration/005 integration workflow.

## Result

The independent Python core searches the Part 2 graph using deterministic A* and
horizontal Euclidean metre weights. Dijkstra uses the same graph as a small-case
verification oracle. Exact endpoint connectors are retained; forbidden and
unresolved candidates are excluded. Every allowed and final route segment is
checked against the continuous vector model; diagonal corner cutting and blocked
boundary contact are excluded. Successful results contain length, runtime,
geometry, exact endpoints and reproducibility metadata.

The UI accepts coordinate edits or a map click for start/end, generates the route,
shows explicit outcomes, exports route GeoJSON and optionally displays an
unvalidated dashed straight-line reference. Changing dataset/endpoints/resolution
clears stale results and aborts outstanding route requests. Source payload
integrity is rechecked even when graph preparation is cached.

The CLI creates `synthetic-route-demo` without network access. Its known wall and
northern passage demonstrate a detour; data, map and export are labeled synthetic.
This model cannot be enabled for a real source manifest. Native rasters retain
the existing population/terrain inspection contracts. Real `braunschweig-part1-v2`
still returns `unresolved_input`; temporary restrictions/legal applicability have
not become verified through implementing a search algorithm.

## Reproduction

From the repository root, after installing the locked dependencies:

```powershell
uv run --project backend --locked uas-planner route-demo --output data/synthetic-route-demo
uv run --project backend --locked uas-planner experiment-route data/synthetic-route-demo --output .cache/demo-route.geojson
uv run --project backend --locked uas-planner experiment-route data/braunschweig-part1-v2 --cell-m 100
```

Dataset directories and export files must be new. Start backend/frontend as in
README, refresh datasets, select the synthetic demo and generate a route.
At default 50 m, the generated detour is approximately **276.222 m**; at 25 m a
different constructed graph can yield a different shortest length. The real
100 m command exits 2 with `unresolved_input`, no route geometry.

## Verification and limits

Hand-calculated fixtures cover cardinal/diagonal distance, equal-cost alternatives,
stable repeated runs, detours, full disconnection, thin obstacles between free
endpoints, obstacle boundary contact, corner cutting, exact off-center connectors,
zero-length cases, invalid/unresolved inputs and search resource limits.
Synthetic API tests compare A* length with Dijkstra within 1e-6 m and verify
resolution changes, source corruption rejection and export metadata. Browser
integration covers map selection, success/export, stale-result invalidation,
invalid and unresolved outcomes and mobile fit. Final validation results and
integration facts are recorded in feedback and HANDOFF.

Endpoint policy uses one containing-cell connector with stable cell-ID ties, no
extra connection radius or direct start-goal edge. Cells intersecting obstacles
are excluded conservatively, so narrow continuous passages may be unavailable.
There is no smoothing, population weighting, time/height optimization or 3D model.
Runtime excludes checksum verification and initial grid preparation. Exports
contain own route geometry and source metadata, excluding source vectors/rasters;
retain source attributions/license strings. Synthetic fixtures are CC0.
