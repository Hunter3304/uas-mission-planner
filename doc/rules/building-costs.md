# Building and tag costs

This page documents the original building analysis and shared classification
policy. The current explorer also analyzes standalone roads, land-use areas and
natural features; see [Independent cost layers](independent-costs.md) for the
extended API, category statistics and independent obstruction flags.

## Source and scope

Carsten Ramke (2020), *Development of advanced informed planning techniques for
BVLOS UAS operations*. Appendix I.II, printed pp. 69-70 (PDF pp. 81-82), Tables
7-1 (landuse), 7-2 (natural), 7-3 (building), 7-4 (highway). The contents list
uses different table numbers; these references follow the actual appendix pages.
The additional `building=barn` example comes from Table 3-3, printed p. 32.

Version: `ramke-building-tags-v1`. Costs are ordinal categories 0 (very low),
1 (low), 2 (medium), 3 (high), 4 (very high). The model encodes research
preferences; it does not predict crash probability or certify flight safety.

Analysis covers saved OSM objects with a nonempty building tag other than `no`.
Counts refer to OSM objects, not deduplicated physical buildings. Points, lines
and polygons can carry building tags. No building is inferred from an address,
amenity, building part, height or geometry alone.

## Building classification

The following values use normalized spellings. Original tags remain unchanged.

| Cost | `building` values |
| --- | --- |
| 0 | `hut`, `shed`, `bunker`, `ruins` |
| 1 | `carport`, `garage`, `garages`, `greenhouse`, `farm_auxiliary`, `shrine` |
| 2 | `parking`, `service`, `yes`, `stable` |
| 3 | `commercial`, `industrial`, `kiosk`, `office`, `retail`, `supermarket`, `warehouse`, `train_station`, `toilets` |
| 4 | `apartments`, `bungalow`, `cabin`, `detached`, `dormitory`, `farm`, `ger`, `hotel`, `house`, `houseboat`, `residential`, `semidetached_house`, `static_caravan`, `terrace`, `stadium`, `school`, `hospital`, `fire_station`, `religious`, `church`, `mosque`, `synagogue`, `cathedral` |

Supplement: `barn` is cost 1 based on Table 3-3, not the appendix table.

The separate paper obstruction list contains `civic`, `fire_station`,
`government`, `hospital`, `kindergarten`, `public`, `school`, `train_station`,
`transportation`, `university`, `grandstand`, `pavilion`, `sports_hall`, `stadium`.
Entries may have both a cost and an obstruction flag. Obstruction-only entries
(for example `kindergarten`) have **no numeric cost**, not cost 0 or 4.
These flags only reproduce the paper's classification. No legal rule engine,
exclusion buffer or flight-permission determination is implemented.

## Other tags on buildings

Each present tag is shown independently. `landuse`, `natural` and `highway` use
their appendix tables, recorded in full in the executable JSON. They do not
increase or replace the building cost. For example, `building=house` gives 4
and `landuse=industrial` gives 3; the building map displays 4, not 7.
`landuse=military` has only a paper obstruction flag. `highway=corridor` is
explicitly excluded by the paper and receives no numeric score.

See the [complete tag cost tables](tag-cost-tables.md) for all values.

Unsupported keys such as `name`, `addr:street`, `height`, `building:levels` and
`amenity` are preserved and marked **Not scored**. In particular,
`building=yes; amenity=school` as two separate tags is still building cost 2;
the amenity does not infer a school cost or obstruction. Classification of
building use from other keys requires a future, separately justified rule.

## Project policy v1 (not rules claimed by the paper)

- Trim whitespace and lowercase supported values for matching only.
- Recognize lists and semicolon-separated values; retain every component result.
  Use the maximum numeric cost within one tag and OR its obstruction flags.
  Never add costs across tag categories. This maximum is a project policy,
  not a claim that the paper specifies multi-value handling.
- Unknown or malformed values in a supported category use provisional cost 2
  and retain `default` status. A multi-value tag containing any unknown component
  retains the default flag even when a known higher cost determines its result.
- Missing/null tags are not scored. Missing/empty building tags and `building=no`
  alone do not identify a building. An uncovered map area is **unassessed**, not 0.
- The paper's spellings `apartements`, `farm_auxilary`, `train_staion` and
  `semidetached-house` are normalized to `apartments`, `farm_auxiliary`,
  `train_station` and `semidetached_house`. Both spellings are accepted.
  The `train_staion` correction means `train_station` carries both cost 3 and
  the historical obstruction flag; this interpretation is explicit in results.
- Unknown building classifications are gray/dashed even if their provisional
  numeric cost is 2 (or higher after multi-value aggregation). Obstruction-only
  buildings are also gray/dashed, with explanatory details. Known cost 2 uses
  the medium color. Dark outlines distinguish paper obstruction flags.

## API and reproducibility

`GET /api/datasets/{id}/features?analysis=building-costs` adds GeoJSON foreign
members `cost_analysis` per feature, and `cost_summary` / `cost_policy` at the
collection level. It retains source properties and geometries. The summary
counts the entire dataset independently of layer visibility or table search.
Default classifications are included in their numeric bin, with a separate
unknown count. The unmatched-tag list includes unknown values in all four
supported categories on building objects.

`GET /api/datasets/{id}/features` and existing downloads still contain the
original dataset. Derived costs are recalculated on read and do not modify
GeoPackage files, manifests or checksums. Downloads are not analysis exports.
Future experiment exports should preserve the rule version and analysis result.

The map is a feature-cost visualization. It does not perform spatial joins,
infer surrounding land use, rasterize uncovered space, fuse population data or
calculate routes. Other-tag analysis applies only to tags already attached to
each building object.
