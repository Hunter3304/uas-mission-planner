import CollapsiblePanel from './CollapsiblePanel'
import { layers, type LayerKey, type BuildingCost, type MapData, type MapFeature } from './types'

const names = {
  building: 'Building',
  highway: 'Road',
  landuse: 'Land use',
  natural: 'Natural feature',
}

export const costColors = ['#26866c', '#80a944', '#d4a326', '#d77732', '#bd3849']
const labels = ['Very low', 'Low', 'Medium', 'High', 'Very high']
export const showValue = (value: unknown) =>
  typeof value === 'string' ? value : JSON.stringify(value)

export function buildingColor(feature: MapFeature) {
  const analysis = feature.cost_analysis
  return !analysis || analysis.has_default || analysis.cost == null
    ? '#78838e'
    : costColors[analysis.cost]
}

export function costText(analysis?: BuildingCost | null) {
  if (!analysis) return 'Not analyzed'
  if (analysis.cost == null) return 'No numeric cost'
  return `${analysis.cost} · ${analysis.has_default ? 'Unknown / default' : analysis.label}`
}

export function CostOverview({
  data,
  enabled,
  onChange,
  layer,
  onLayerChange,
}: {
  data: MapData
  layer: LayerKey
  onLayerChange: (layer: LayerKey) => void
  enabled: boolean
  onChange: (enabled: boolean) => void
}) {
  const name = names[layer]
  const summary = data.cost_summary
  if (!summary)
    return (
      <p className="empty-note">
        Tag cost analysis unavailable. Restart the backend to load the analysis API.
      </p>
    )
  return (
    <CollapsiblePanel className="cost-overview" title={`${name} cost analysis`} badge={<span className="count-pill">{summary.buildings} {layer === 'building' ? 'buildings' : 'objects'}</span>}>
      <div className="section-row">
        <label className="cost-toggle">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => onChange(event.target.checked)}
          />{' '}
          {name} cost map
        </label>
      </div>
      <label className="cost-layer-select">
        Cost category{' '}
        <select
          aria-label="Cost category"
          value={layer}
          onChange={(event) => onLayerChange(event.target.value as LayerKey)}
        >
          {layers.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <p>
        Colors show the <strong>{layer} tag cost</strong>. Other tags are assessed separately in
        feature details.
      </p>
      <div className="cost-legend">
        {labels.map((label, level) => (
          <span key={label}>
            <i style={{ background: costColors[level] }} />
            {level} · {label}
            <strong>{summary.levels[String(level)]}</strong>
          </span>
        ))}
        <span>
          <i style={{ background: '#78838e' }} />
          Unknown / no numeric cost
        </span>
      </div>
      <p data-testid="cost-summary">
        {summary.defaulted} {layer === 'building' ? 'buildings' : 'objects'} with unknown values
        (fallback 2 per unknown value) · {summary.without_numeric_cost} without numeric cost ·{' '}
        {summary.obstruction_flagged} paper obstruction flags
      </p>
      <p className="cost-note">
        Counts cover all saved objects in this category, including hidden ones. Numeric counts
        include provisional results; mixed tags can have a cost above 2. Gray dashed shapes indicate
        unknown or unscored costs. Dark outlines mark historical paper obstruction flags. Blank
        areas are unassessed.
      </p>
      <p className="cost-note">
        Only saved features are analyzed. Background map images and newly viewed areas do not add
        analysis data. Category costs are independent; no fusion or road-width model is applied.
      </p>
      <details>
        <summary>Rules and unmatched tags</summary>
        <p>
          {data.cost_policy?.source} · {data.cost_policy?.version}
        </p>
        <p>
          {data.cost_policy?.aggregation} {data.cost_policy?.limits}
        </p>
        {summary.unmatched_tags.length ? (
          <ul>
            {summary.unmatched_tags.map((tag, index) => (
              <li key={index}>
                <code>
                  {tag.key}={showValue(tag.value)}
                </code>{' '}
                · {tag.count} objects · default 2
              </li>
            ))}
          </ul>
        ) : (
          <p>No unmatched values in supported tag categories.</p>
        )}
      </details>
    </CollapsiblePanel>
  )
}

export function CostDetails({ analysis, layer }: { analysis: BuildingCost; layer: LayerKey }) {
  const name = names[layer]
  return (
    <section className="cost-details" aria-label={`Selected ${name.toLowerCase()} costs`}>
      <h4>
        {name} cost: {costText(analysis)}
      </h4>
      {analysis.obstruction && (
        <p className="obstruction-note">
          Paper obstruction flag. Current flight restrictions have not been assessed.
        </p>
      )}
      <p>Rule version: {analysis.rule_version}. Tag costs are not added together.</p>
      {analysis.tags.map((tag) => (
        <details className="tag-cost" key={tag.key} open={tag.key === layer}>
          <summary>
            <span>
              {tag.key}={showValue(tag.value)}
            </span>
            <strong>
              {tag.cost == null
                ? tag.status === 'unscored'
                  ? 'Not scored'
                  : 'No numeric cost'
                : `Cost ${tag.cost}${tag.has_default ? ' (default)' : ''}`}
            </strong>
          </summary>
          <p>{tag.reason}</p>
          {tag.matches.map((match, index) => (
            <div className="cost-match" key={index}>
              <p>
                <code>
                  {tag.key}={match.normalized ?? '(malformed value)'}
                </code>{' '}
                · {match.status}
                {match.cost != null ? ` · cost ${match.cost}` : ''}
              </p>
              <p>{match.reason}</p>
              <small>{match.source}</small>
            </div>
          ))}
          {!tag.matches.length && <small>{tag.source}</small>}
        </details>
      ))}
    </section>
  )
}
