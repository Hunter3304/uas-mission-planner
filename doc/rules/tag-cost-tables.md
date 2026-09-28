# Complete tag cost tables

Readable reference for `ramke-building-tags-v1`. The executable JSON remains the
single source used by the classifier. Update this reference when changing rules.

Source: Ramke (2020), Appendix I.II, printed pp. 69-70. Values below use the
documented spelling corrections. See [policy and interpretation](building-costs.md).

## `building`

Table 7-3, p. 70

| Cost | Tag values |
| --- | --- |
| 0 | `hut`, `shed`, `bunker`, `ruins` |
| 1 | `carport`, `garage`, `garages`, `greenhouse`, `farm_auxiliary`, `shrine` |
| 2 | `parking`, `service`, `yes`, `stable` |
| 3 | `commercial`, `industrial`, `kiosk`, `office`, `retail`, `supermarket`, `warehouse`, `train_station`, `toilets` |
| 4 | `apartments`, `bungalow`, `cabin`, `detached`, `dormitory`, `farm`, `ger`, `hotel`, `house`, `houseboat`, `residential`, `semidetached_house`, `static_caravan`, `terrace`, `stadium`, `school`, `hospital`, `fire_station`, `religious`, `church`, `mosque`, `synagogue`, `cathedral` |

**Paper obstruction flags:** `civic`, `fire_station`, `government`, `hospital`, `kindergarten`, `public`, `school`, `train_station`, `transportation`, `university`, `grandstand`, `pavilion`, `sports_hall`, `stadium`.

Supplement: `building=barn` has cost 1, from Ramke (2020), Table 3-3, p. 32.

Excluded from scoring: `no`.

## `landuse`

Table 7-1, p. 69

| Cost | Tag values |
| --- | --- |
| 0 | `reservoir`, `farmland`, `farmyard`, `vineyard`, `meadow`, `orchard`, `salt_pond` |
| 1 | `basin`, `landfill`, `quarry` |
| 2 | `brownfield`, `grass`, `greenfield`, `greenhouse_horticulture`, `plant_nursery`, `village_green` |
| 3 | `allotments`, `retail`, `commercial`, `industrial`, `construction`, `cemetery`, `garage` |
| 4 | `residential`, `railway`, `recreation_ground`, `religious` |

**Paper obstruction flags:** `military`.

## `natural`

Table 7-2, p. 69

| Cost | Tag values |
| --- | --- |
| 0 | `wood`, `water`, `glacier` |
| 1 | `scrub`, `heath`, `grassland`, `fell`, `bare_rock`, `scree`, `shingle`, `sand`, `mud`, `wetland`, `bay`, `cape`, `strait` |
| 2 | `beach` |
| 3 | None |
| 4 | None |

**Paper obstruction flags:** None.

## `highway`

Table 7-4, p. 70

| Cost | Tag values |
| --- | --- |
| 0 | `escape`, `track` |
| 1 | `service`, `raceway`, `bridleway` |
| 2 | `unclassified`, `residential`, `living_street`, `road`, `path` |
| 3 | `secondary`, `secondary_link`, `tertiary`, `tertiary_link`, `pedestrian`, `bus_guideway`, `footway`, `steps`, `cycleway` |
| 4 | `motorway`, `motorway_link`, `trunk`, `trunk_link`, `primary`, `primary_link` |

**Paper obstruction flags:** None.

Excluded from scoring: `corridor`.
