import type { Feature, FeatureCollection, Geometry } from 'geojson'

export type ExternalFeature = Feature<Geometry, Record<string, unknown>> & { source_layer?: string }
export interface Experiment {
  synthetic: boolean
  saved_at_utc: string
  config: {
    scenario: string
    agl_m: number
    timezone: string
    mission_start: string
    mission_end: string
    ghsl_epoch: number
    start: [number, number]
    end: [number, number]
  }
  sources: Record<
    string,
    {
      product: string
      source_id: string
      attribution: string
      license: string
      vertical_datum?: string
      coverage?: string
      metadata_discrepancy?: string
      raster?: { resolution: number[]; nodata: number | null; effective_nodata: number }
    }
  >
}
export interface ExternalOverlays {
  population: FeatureCollection
  zones: FeatureCollection
  showPopulation: boolean
  showZones: boolean
  experiment: Experiment
  onFeature: (feature: ExternalFeature) => void
  onLocation: (lon: number, lat: number) => void
  grid?: GridData
  showGrid?: boolean
  onCell?: (cell: GridCell) => void
  route?: RouteResult | null
  endpoints?: { start: [number, number]; end: [number, number] }
  showReference?: boolean
}
export interface RouteResult {
  status: string
  message?: string
  geometry: Geometry | null
  length_m: number | null
  risk_length_cost?: number | null
  objective_cost?: number | null
  algorithm: string
  objective: string
  exact: boolean
  solution_kind: string
  optimality: string
  assumptions: unknown
  risk_model?: unknown
  controls?: unknown
  candidate?: unknown
  runtime_ms: number
  rules_version: string
  experiment: { synthetic: boolean }
  connectors?: GridData['connectors']
}
export interface GridCell {
  id: string
  geometry: Geometry
  state: string
  terrain_m: number | null
  aircraft_altitude_m: number | null
  population: { estimated_people: number | null; people_per_km2: number | null; unknown_area_m2: number; native_support_m: number }
  reasons: { source: string; reason: string }[]
}
export interface GridData {
  cell_size_m: number
  cell_count: number
  edge_count: number
  policy: string
  cells: GridCell[]
  edges: { from: string; to: string; length_m: number; state: string; reasons: { source: string; reason: string }[] }[]
  connectors: { endpoint: string; cell: string; length_m: number; state: string; reasons: { source: string; reason: string }[] }[]
}
export const populationColor = (value: unknown) =>
  value == null
    ? '#747b86'
    : Number(value) === 0
      ? '#f1f9eb'
      : Number(value) < 25
        ? '#b7dea3'
        : Number(value) < 100
          ? '#48a47b'
          : '#005c4b'

export interface ComparisonReport {
  status: string
  synthetic: boolean
  runs: { label: string; result: RouteResult; comparison_costs: {
    status: string; length_m?: number; risk_length_cost?: number; objective_cost?: number
  } }[]
  abitstar_summary: { verified_exact_solution_rate: number; repetitions: number;
    seed_supported: boolean; objective_distribution: { min: number; max: number; mean: number; median: number } | null }
  limitations: string[]
}
