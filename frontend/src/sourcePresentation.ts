import { layers } from './types'
import type { MapSelection } from './mapSelection'

export const costLabels = ['Very low', 'Low', 'Medium', 'High', 'Very high']
export const asRecord = (value: unknown): Record<string, unknown> =>
  value != null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
export const sourceText = (value: unknown) => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : undefined
export const numberText = (value: number) => new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 }).format(value)
export const fieldLabel = (key: string) => key.replace(/[_:]/g, ' ').replace(/^./, value => value.toUpperCase())
export const categoryNames = (categories: unknown) => Array.isArray(categories)
  ? categories.map(key => layers.find(layer => layer.key === key)?.label ?? String(key)).join(', ')
  : ''

export function objectTitle(properties: Record<string, unknown>, fallback = 'OSM object') {
  const name = sourceText(properties.name)
  if (name) return name
  for (const [key, label] of [['building', 'Building'], ['highway', 'Road / path'], ['landuse', 'Land use'], ['natural', 'Natural feature']]) {
    const value = sourceText(properties[key])
    if (value) return value === 'yes' ? label : `${label} · ${value.replaceAll('_', ' ')}`
  }
  return categoryNames(properties.categories) || fallback
}

export function populationSummary(properties: Record<string, unknown>) {
  if (properties.layer_kind === 'population_cost') {
    const score = properties.risk_score
    return typeof score === 'number' && Number.isInteger(score) && score >= 0 && score <= 4
      ? { known: true, text: `Population risk: ${score} · ${costLabels[score]}`, note: '250 m aggregate · ordinal class, not a probability. Class 0 can contain people.' }
      : { known: false, text: 'NoData · population risk unavailable', note: 'Incomplete population support is not zero population or class 0.' }
  }
  const value = properties.people_per_cell
  if (properties.status === 'unknown' || typeof value !== 'number' || !Number.isFinite(value) || value < 0)
    return { known: false, text: 'NoData · population unavailable', note: 'Missing population data is not zero population.' }
  const estimate = value > 0 && value < 0.01 ? 'less than 0.01' : numberText(value)
  return { known: true, text: `Estimated population: ${estimate} people per native cell`, note: value === 0 ? 'Known zero estimate · very pale green on the map.' : 'A modelled estimate, not an exact headcount or the number exposed to a flight.' }
}

export function decisionSummary(properties: Record<string, unknown>) {
  const state = sourceText(properties.state)
  if (properties.policy_exclusion === true || state === 'unresolved')
    return { label: properties.policy_exclusion === true ? 'Policy exclusion · unresolved' : 'Unresolved assessment', tone: 'uncertain', note: 'Unresolved applicability is not a confirmed prohibition. A policy exclusion avoids the area under the selected planning policy.' }
  if (state === 'prohibited') return { label: 'Assessed prohibition', tone: 'blocked', note: 'Applies to the supplied assessment scope; it does not describe every flight or time.' }
  if (state === 'blocked') return { label: properties.category === 'building_obstacle' ? 'Building obstacle' : 'Assessed constraint', tone: 'blocked', note: 'This assessed constraint applies to the supplied scenario. It is not a blanket source-zone ban.' }
  if (state === 'conditional_allowed') return { label: 'Conditions satisfied · scoped evidence', tone: 'scoped', note: 'Evidence covers the stated conditions and scope only; this is not general flight permission.' }
  if (state === 'not_applicable') return { label: 'Not applicable to this scenario', tone: 'neutral', note: 'Outside the assessed scope. This is not a general permission.' }
  return { label: state ? fieldLabel(state) : 'Assessment not supplied', tone: 'neutral', note: 'No further permission or prohibition is inferred from this record.' }
}

export function selectionTitle(item: MapSelection) {
  const p = item.feature.properties ?? {}
  if (item.aggregate) return 'Aggregate overview cell'
  if (item.osm) return objectTitle(p)
  if (item.source === 'GHSL') return `${p.layer_kind === 'population_cost' ? '250 m population risk' : 'Population cell'} · ${item.id}`
  return sourceText(p.name) ?? sourceText(p.type) ?? (p.category === 'building_obstacle' ? 'Assessed building footprint' : item.source === 'DIPUL' ? 'Assessed DIPUL zone' : 'Scenario area')
}

export function selectionSummary(item: MapSelection) {
  const p = item.feature.properties ?? {}
  if (item.aggregate) return `${p.objects ?? 'Unknown'} assigned objects. ${Object.entries(asRecord(p.category_counts)).map(([key, value]) => `${categoryNames([key])}: ${value}`).join(' · ')}. Zoom for individual objects; no cost score.`
  if (item.source === 'GHSL') return populationSummary(p).text
  if (item.osm) return 'Original source tags and independent category costs in the left inspector.'
  return decisionSummary(p).label
}
