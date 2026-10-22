import { layers, type CostScore, type LayerKey, type Visibility } from './types'

export const costColors = ['#26866c', '#80a944', '#d4a326', '#d77732', '#bd3849']
export const unknownCostColor = '#78838e'

export function costColor(score?: CostScore | null) {
  return !score || score.has_default || score.cost == null
    ? unknownCostColor
    : (costColors[score.cost] ?? unknownCostColor)
}

// The first enabled membership in demo order wins. Hiding a higher-priority
// category exposes the next membership; original tags are never changed.
export function categoryColor(categories: readonly LayerKey[], visibility: Visibility) {
  return layers.find(({ key }) => categories.includes(key) && visibility[key])?.color ?? '#7c8b91'
}

export function osmStyle(
  categories: readonly LayerKey[],
  visibility: Visibility,
  costMode: boolean,
  score?: CostScore | null,
) {
  const color = costMode ? costColor(score) : categoryColor(categories, visibility)
  return {
    color: costMode && score?.obstruction ? '#202c3b' : color,
    fillColor: color,
    weight: costMode && score?.obstruction ? 4 : 3,
    fillOpacity: costMode ? 0.65 : 0.25,
    dashArray: costMode && (!score || score.has_default || score.cost == null) ? '5 4' : undefined,
  }
}
