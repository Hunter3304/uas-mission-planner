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
