# Independent cost layers

The explorer analyzes `building`, `highway`, `landuse` and `natural` separately
on every saved feature. A road, land-use polygon or natural point needs no
building tag. The numeric classification tables remain `ramke-building-tags-v1`;
see the [complete tables](tag-cost-tables.md) and
[classification policy](building-costs.md). The version names the existing
ruleset, whose four tables have not changed in this extension.

## Using the explorer

1. Load a saved dataset and select **Cost category**.
2. Enable its cost-map checkbox (for example **Road cost map**).
3. Select a shape or table row for the original tags, individual scores,
   rule sources and explanations. The selected category's tag opens first.
4. Change categories to update colors, table costs and distribution counts.
   The old feature selection is cleared. The cost-map toggle stays enabled.

The selected category alone controls the numeric cost, default marker and paper
obstruction outline. For example, an object tagged `highway=footway` and
`landuse=recreation_ground` has road cost 3 and land-use cost 4, not cost 7.
An object tagged `building=yes` and `landuse=military` has building cost 2
without a building obstruction flag; its land-use result is obstruction-only
with no numeric score. Other-tag evidence remains visible in details.

Distribution counts cover the full saved dataset for the selected category,
independent of table search and layer visibility. A multi-tag object counts once
within each matching category; category counts must not be added to obtain the
number of unique objects. Existing layer switches retain union semantics:
an object with both road and land-use tags remains visible if either is enabled.

## Unknown, excluded and absent values

- Known zero costs (for example `natural=water`) are scored and colored normally.
- Unknown values use provisional cost 2 and gray dashed styling. For example,
  the paper's natural table does not classify `tree`; it remains explicitly
  unknown rather than being silently mapped to `wood`.
- `highway=corridor` is excluded from scoring and shown without numeric cost.
- `landuse=military` has only a historical paper obstruction flag, not cost 0.
- Missing, null, empty or `no`-only category tags do not identify that category.
- Other metadata, including names and addresses, remains unscored.

## API

`GET /api/datasets/{id}/features?analysis=tag-costs` returns original geometry
and properties, with `layer_analyses` on each feature and `layer_summaries` on
the collection, both keyed by the four tag names. Each summary includes a
`features` count, numeric bins, default counts, paper obstruction counts,
no-numeric-cost counts and unmatched values for that category only.

Top-level `cost_analysis` and `cost_summary` retain the building view as a
convenience. Use the keyed results for category switching. The older
`analysis=building-costs` request is still supported and retains its earlier
aggregate paper-flag behavior. The UI now uses `analysis=tag-costs` and each
category's independent flags.

Raw feature requests and downloads are unchanged. Results are computed on read;
saved GeoPackages and manifests are not rewritten. No new acquisition is needed.

## Scope

Only saved features are analyzed. Basemap tiles are context images and panning
does not fetch new analysis data. Line width is a display style, not a physical
road-width model. This extension does not create a cost grid, spatially join
neighboring areas, fuse category costs, or change the acquisition/viewport scope.
