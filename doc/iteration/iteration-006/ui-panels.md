# Explorer panel refinement — Issue #61

User requirements confirmed on 2026-10-02:

- Building cost analysis, Independent source layers, Route planning, Location
  and source inspection, Feature browser and Feature details can expand/collapse.
- Feature browser and details always exist, initially collapsed, manually
  expandable. Selecting any feature expands both; clearing selection folds both.
- Only Risk weight, Distance weight and Background score assumption depend on
  the Weighted building risk objective. Safety distance and ABIT* budget stay visible.

A shared panel component exposes labelled buttons, aria-expanded and aria-controls.
Hidden content remains mounted, preserving input state and generated route results.
Route planning is independent of source layers; all panels are outside the map.
Feature selection remounts the two feature panels to apply the selection state.
Other panels initially remain expanded. No backend/planner calculation changed.

## Validation

- `npm run lint` and `npm run build`: passed.
- `npm run test:e2e`: 9 passed (Chrome).
- `npm run test:smoke -- --workers=1`: 11 passed, 27.9 seconds.
- Smoke environment: PLAYWRIGHT_CHANNEL=chrome, PYTHONUTF8=1; existing Windows
  OMPL extra retained by the smoke configuration.
- Real API checks cover independent folds, manual feature expansion, selection
  and clearing, preserved weights/background/results, route/export/comparison
  regression and a 390 px viewport without horizontal overflow.
- Mobile capture `.cache/ui-panels-mobile.png` visually reviewed (generated, ignored).

This UI branch is based on feature/60-planner-controls while the Part 2/3 parent
implementation awaits integration. The separate PR isolates the UI changes.
