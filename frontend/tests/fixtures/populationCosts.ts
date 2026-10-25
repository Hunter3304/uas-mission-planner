export function populationCosts(score: number | null = 0, people = 0) {
  return {
    identity: 'population-class-fixture', version: 'ramke-population-250m-v1', state: 'ready',
    epoch: 2020, maximum_people_per_km2: 10000, all_zero: false,
    known_cells: score == null ? 0 : 1, unknown_cells: score == null ? 1 : 0,
    source: { product: 'GHS-POP test', sha256: 'population-fixture' },
    bins: Array.from({ length: 5 }, (_, i) => ({ score: i, lower_people_per_km2: i * 2000, upper_people_per_km2: (i + 1) * 2000, upper_inclusive: i === 4 })),
    display: { complete: true, returned_count: 1, matched_count: 1, bounds: null },
    layer: { type: 'FeatureCollection', features: [{ type: 'Feature', id: 'population250:0:0',
      geometry: { type: 'Polygon', coordinates: [[[9.799, 52.387], [9.801, 52.387], [9.801, 52.389], [9.799, 52.389], [9.799, 52.387]]] },
      properties: { layer_kind: 'population_cost', risk_score: score, status: score == null ? 'unknown' : 'known',
        estimated_people: score == null ? null : people, observed_estimated_people: people,
        people_per_km2: score == null ? null : people * 16, native_support_m: 100, cell_size_m: 250, epoch: 2020,
        unknown_area_m2: score == null ? 10000 : 0, native_support_area_m2: 62500,
        density_bin: { lower_people_per_km2: (score ?? 0) * 2000, upper_people_per_km2: ((score ?? 0) + 1) * 2000, upper_inclusive: score === 4 },
      },
    }] },
  }
}
