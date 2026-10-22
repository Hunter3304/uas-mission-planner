import { createContext, useContext } from 'react'
import type { Feature, Geometry } from 'geojson'

export type InspectableFeature = Feature<Geometry | null, Record<string, unknown> | null>
export interface MapSelection {
  owner: string
  id: string
  version: unknown
  source: 'OSM' | 'DIPUL' | 'GHSL' | 'Scenario'
  feature: InspectableFeature
  anchor?: [number, number]
  aggregate?: boolean
  diagnostic?: boolean
  osm?: { base: string; key: string; snapshot: string }
  zoom?: () => void
}
export interface SelectionActions {
  select: (item: MapSelection) => void
  clear: () => void
  reconcile: (owner: string, features: readonly InspectableFeature[] | null, version: unknown) => void
  invalidate: (owner: string, id: string, version: unknown, message: string) => void
  showDetails: () => void
}
export const MapSelectionContext = createContext<SelectionActions | null>(null)
export function useMapSelection() {
  const actions = useContext(MapSelectionContext)
  if (!actions) throw new Error('Map selection requires its regional provider.')
  return actions
}
export function snapshotKey(value: object) {
  return JSON.stringify(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)))
}
export function selectionFeatureId(feature: InspectableFeature) {
  const p = feature.properties ?? {}
  return String(feature.id ?? (p.osm_id != null ? `${p.element_type}/${p.osm_id}` : p.source ?? p.cell_id ?? JSON.stringify([feature.geometry, p])))
}
