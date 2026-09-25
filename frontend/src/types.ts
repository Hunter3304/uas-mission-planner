import type { Feature, FeatureCollection, Geometry } from 'geojson'

export const layers = [
  { key: 'building', label: 'Buildings', color: '#bc784a' },
  { key: 'highway', label: 'Roads & paths', color: '#657ac0' },
  { key: 'landuse', label: 'Land use', color: '#b7983c' },
  { key: 'natural', label: 'Natural features', color: '#26877a' },
] as const
export type LayerKey = (typeof layers)[number]['key']
export type Visibility = Record<LayerKey, boolean>
export type MapFeature = Feature<Geometry, Record<string, unknown>>
export type MapData = FeatureCollection<Geometry, Record<string, unknown>>
export interface Dataset {
  id: string
  verified: boolean
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
export function isVisible(feature: MapFeature, visibility: Visibility) {
  return featureLayers(feature).some(({ key }) => visibility[key])
}
