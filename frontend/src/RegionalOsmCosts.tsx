import type { BuildingCost, LayerKey } from './types'
import { AttributeValue, SourceFacts } from './SourceFacts'
import { costLabels } from './sourcePresentation'

const names = { building: 'Building', highway: 'Road', landuse: 'Land use', natural: 'Natural feature' }
const scoreText = (score: number | null) => score == null ? 'No numeric cost' : `${score} · ${costLabels[score] ?? 'Unlabelled score'}`

export default function RegionalOsmCosts({ analysis, layer }: { analysis: BuildingCost; layer: LayerKey }) {
  return <section className="regional-cost-card" aria-label={`Selected ${names[layer].toLowerCase()} costs`}>
    <SourceFacts title={`${names[layer]} cost: ${scoreText(analysis.cost)}`}>
      {analysis.has_default && <p className="source-decision uncertain">Provisional · includes unknown/default values</p>}
      <p>Independent ordinal category cost, not flight permission or an overall risk score. Costs are not added across categories or tags.</p>
      {analysis.obstruction && <p className="source-interpretation">Historical paper obstruction flag · dark map outline. This flag is not an assessment of current flight restrictions.</p>}
      {analysis.has_default && <p>Unknown tag values use the existing default rule. The displayed result may also include known matches; it is shown gray and dashed.</p>}
      <details className="source-disclosure"><summary>Matched rules and evidence</summary>
        <p>Rule version: {analysis.rule_version}</p>
        {analysis.tags.length ? analysis.tags.map(tag => <section className="source-rule" key={tag.key}>
          <h5>{tag.key}</h5><AttributeValue value={tag.value} /><p>{scoreText(tag.cost)}{tag.has_default ? ' · provisional default' : ''}</p><p>{tag.reason}</p>
          {tag.matches.map((match, index) => <div className="source-rule-match" key={index}><p>{match.normalized ?? 'Malformed value'} · {match.status.replaceAll('_', ' ')} · {scoreText(match.cost)}</p><p>{match.reason}</p><small>{match.source}</small></div>)}
          {!tag.matches.length && <small>{tag.source}</small>}
        </section>) : <p>No individual rule matches supplied.</p>}
      </details>
    </SourceFacts>
  </section>
}
