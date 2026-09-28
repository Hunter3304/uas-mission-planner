import type { Feature, FeatureCollection, Geometry } from 'geojson'

export const layers = [
  { key: 'building', label: 'Buildings', color: '#bc784a' },
  { key: 'highway', label: 'Roads & paths', color: '#657ac0' },
  { key: 'landuse', label: 'Land use', color: '#b7983c' },
  { key: 'natural', label: 'Natural features', color: '#26877a' },
] as const
export type LayerKey = (typeof layers)[number]['key']
export type Visibility = Record<LayerKey, boolean>
export interface CostMatch {
  input: string | null
  normalized: string | null
  cost: number | null
  status: string
  obstruction: boolean
  source: string
  reason: string
}
export interface TagCost {
  key: string
  value: unknown
  cost: number | null
  status: string
  obstruction: boolean
  has_default: boolean
  matches: CostMatch[]
  reason: string
  source: string
}
export interface BuildingCost {
  rule_version: string
  cost: number | null
  label: string
  status: string
  has_default: boolean
  obstruction: boolean
  tags: TagCost[]
}
export type MapFeature = Feature<Geometry, Record<string, unknown>> & {
  cost_analysis?: BuildingCost | null
  layer_analyses?: Partial<Record<LayerKey, BuildingCost | null>>
}
export interface LayerSummary {
  features: number
  levels: Record<string, number>
  defaulted: number
  obstruction_flagged: number
  without_numeric_cost: number
  unmatched_tags: { key: string; value: unknown; count: number }[]
}
export type MapData = Omit<FeatureCollection<Geometry, Record<string, unknown>>, 'features'> & {
  features: MapFeature[]
  layer_summaries?: Partial<Record<LayerKey, LayerSummary>>
  cost_summary?: {
    buildings: number
    levels: Record<string, number>
    defaulted: number
    obstruction_flagged: number
    without_numeric_cost: number
    unmatched_tags: { key: string; value: unknown; count: number }[]
  }
  cost_policy?: {
    version: string
    source: string
    scope: string
    aggregation: string
    unknown: string
    limits: string
  }
}
export interface Dataset {
  id: string
  verified: boolean
  synthetic?: boolean
  source?: string
  error?: string
  feature_count: number
  crs: string
  geometry_counts: Record<string, number>
  layer_counts: Record<LayerKey, number>
  query_bounds: { west: number; south: number; east: number; north: number }
  feature_bounds: number[] | null
  query_area_km2: number
  saved_at_utc: string | null
  acquisition_finished_at_utc: string | null
  invalid_geometry_count: number
  sha256: string
}

export function featureKey(feature: MapFeature) {
  return `${feature.properties.element_type}/${feature.properties.osm_id}`
}
export function featureLayers(feature: MapFeature) {
  return layers.filter(({ key }) => feature.properties[key] != null)
}
export function isVisible(feature: MapFeature, visibility: Visibility, costMode = false) {
  return (
    (!costMode || feature.cost_analysis != null) &&
    featureLayers(feature).some(({ key }) => visibility[key])
  )
}
