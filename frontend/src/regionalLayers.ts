import type { Feature, FeatureCollection } from 'geojson'
import type { ConstraintLayers } from './RegionalMap'

export const decisionKeys = ['blocked', 'excluded', 'allowed', 'inactive', 'unknown'] as const
export type DecisionKey = typeof decisionKeys[number]
export type LayerSource = 'osm' | 'dipul' | 'coverage'
export type ScenarioLayerKey = `${LayerSource}:${DecisionKey}`
export const initialScenarioVisibility: Record<ScenarioLayerKey, boolean> = {
  'osm:blocked': true, 'osm:unknown': false, 'osm:excluded': false, 'osm:allowed': false, 'osm:inactive': false,
  'dipul:blocked': true, 'dipul:excluded': true, 'dipul:allowed': false, 'dipul:inactive': false, 'dipul:unknown': false,
  'coverage:blocked': false, 'coverage:excluded': false, 'coverage:allowed': false, 'coverage:inactive': false, 'coverage:unknown': false,
}

function sourceOf(feature: Feature): LayerSource {
  const p = feature.properties ?? {}
  if (p.category === 'building_obstacle' || /^OSM\b/.test(String(p.source))) return 'osm'
  // Reviewed temporary notices and unclassified findings are not original DIPUL.
  if (String(p.source).startsWith('dipul:')) return 'dipul'
  return 'coverage'
}

export function groupScenarioLayers(data: ConstraintLayers | null) {
  const groups = {} as Record<ScenarioLayerKey, FeatureCollection>
  for (const source of ['osm', 'dipul', 'coverage'] as const)
    for (const decision of decisionKeys) groups[`${source}:${decision}`] = { type: 'FeatureCollection', features: [] }
  if (data)
    for (const decision of decisionKeys)
      for (const feature of data[decision]?.features ?? [])
        groups[`${sourceOf(feature)}:${decision}`].features.push(feature)
  return groups
}
