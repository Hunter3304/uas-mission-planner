# Research and routing rules

This directory documents implemented cost classification and routing rules.

[Constrained shortest-path routing](routing-algorithms.md) specifies the confirmed
A* planner and Dijkstra verification roles implemented in Part 3. Routing does
not change the independent cost layers.

## Implemented cost rules
Start with [Independent cost layers](independent-costs.md) for current UI and API behavior.
Start with [Building and tag costs](building-costs.md) for the classification table,
source citations, interpretation and project-specific decisions. The
[complete tag cost tables](tag-cost-tables.md) list all four supported categories
in a readable format, including the building and highway tables from the appendix.

The single executable source is
[`cost_rules.json`](../../backend/src/uas_planner/core/cost_rules.json), packaged
with the independent Python core. The frontend receives results from the core;
it contains no duplicate classification table. No database migration or new
OSM download is needed to analyze a saved dataset.

## Updating a cost classification rule

1. Identify its source and explain the research assumption.
2. Edit the JSON and increment its `version` when behavior changes.
3. Update the documentation, recording deviations from the paper.
4. Run classifier/API tests and the real-stack browser smoke test.
5. Restart the backend and refresh the dataset to apply the new version.

Preserve rule versions with experiment results. Ordinal costs are not measured
accident probabilities. Historical paper obstruction flags do not establish
current legal restrictions.
