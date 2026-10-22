import type { MapSelection } from './mapSelection'
import { AttributeList, Fact, OriginalAttributes, SourceFacts } from './SourceFacts'
import { asRecord, categoryNames, decisionSummary, numberText, populationSummary, sourceText } from './sourcePresentation'

function HeightLimit({ properties, prefix }: { properties: Record<string, unknown>; prefix: 'lower' | 'upper' }) {
  const value = sourceText(properties[`${prefix}_limit_altitude`])
  const unit = sourceText(properties[`${prefix}_limit_unit`])
  const reference = sourceText(properties[`${prefix}_limit_alt_ref`])
  return <Fact label={prefix === 'lower' ? 'Lower limit' : 'Upper limit'}>{value == null ? 'Not supplied' : `${value} ${unit ?? '(unit not supplied)'} · ${reference ?? 'reference not supplied'}`}</Fact>
}

function PopulationDetails({ item }: { item: MapSelection }) {
  const p = item.feature.properties ?? {}, context = item.context ?? {}
  const summary = populationSummary(p)
  const resolution = p.native_support_m ?? context.native_support_m
  const epoch = p.epoch ?? context.epoch
  return <>
    <SourceFacts title="Population estimate"><p className="source-main-value">{summary.text}</p><p>{summary.note}</p>{!summary.known && <p>NoData cells are gray on the map.</p>}<dl>
      <Fact label="Native resolution">{typeof resolution === 'number' && resolution > 0 ? `${numberText(resolution)} m × ${numberText(resolution)} m` : 'Not supplied'}</Fact>
      <Fact label="Epoch">{sourceText(epoch) ?? 'Not supplied'}</Fact>
      <Fact label="Cell identity">{item.id}</Fact>
      {sourceText(context.product) && <Fact label="Product">{sourceText(context.product)}</Fact>}
    </dl></SourceFacts>
    <SourceFacts title="Coverage and interpretation"><p>Cell values describe the full native cell, not a clipped viewport total. Population is inspection only and does not change the route cost.</p>
      {typeof context.complete_support === 'boolean' && <p>{context.complete_support ? 'The requested inspection area has complete population support.' : 'The requested inspection area has incomplete population support; known cells do not establish complete regional coverage.'}</p>}
      {sourceText(context.interpretation) && <p>{sourceText(context.interpretation)}</p>}
    </SourceFacts>
    <OriginalAttributes values={p} />
    {Object.keys(context).length > 0 && <details className="source-disclosure"><summary>Population source and query provenance</summary><AttributeList values={context} /></details>}
  </>
}

export default function RegionalSourceDetails({ item }: { item: MapSelection }) {
  const p = item.feature.properties ?? {}, context = item.context ?? {}
  if (item.aggregate) return <>
    <SourceFacts title="Aggregate overview"><p className="source-main-value">{sourceText(p.objects) ?? 'Unknown'} assigned objects</p><p>This is not an individual OSM object or a cost score.</p><dl>
      {Object.entries(asRecord(p.category_counts)).map(([key, value]) => <Fact key={key} label={categoryNames([key])}>{sourceText(value) ?? 'Not supplied'}</Fact>)}
    </dl><p>Whole cells intersecting the view are counted using one representative point per object. Counts are not exact viewport totals; category memberships overlap.</p><button type="button" onClick={item.zoom}>Zoom for objects</button></SourceFacts>
  </>
  if (item.source === 'GHSL') return <PopulationDetails item={item} />
  const decision = decisionSummary(p), scenario = asRecord(context.scenario)
  const msl = asRecord(p.zone_msl_bounds_m)
  const originalOsm = item.source === 'OSM' ? sourceText(p.source)?.match(/^(node|way|relation)\/([0-9]+)$/) : null
  const original = ['name', 'type', 'layer', 'source', 'legal_reference', 'legal_ref', 'valid_from', 'valid_until', 'schedule']
  return <>
    <SourceFacts title="Scenario assessment"><p className={`source-decision ${decision.tone}`}>{decision.label}</p><p>{sourceText(p.reason) ?? 'No assessment reason supplied.'}</p><p className="source-interpretation">{decision.note}</p><dl>
      {sourceText(p.vertical_relation) && <Fact label="Vertical relation">{sourceText(p.vertical_relation)?.replaceAll('_', ' ')}</Fact>}
      {p.clearance_m != null && <Fact label="Additional clearance">{sourceText(p.clearance_m)} m</Fact>}
      {p.buffer_m != null && <Fact label="Source buffer">{sourceText(p.buffer_m)} m</Fact>}
      {sourceText(p.scope) && <Fact label="Assessment scope">{sourceText(p.scope)}</Fact>}
      {sourceText(p.required_review) && <Fact label="Required review">{sourceText(p.required_review)?.replaceAll('_', ' ')}</Fact>}
      {scenario.agl_m != null && <Fact label="Assessed flight height">{sourceText(scenario.agl_m)} m AGL</Fact>}
      {sourceText(scenario.mission_start) && <Fact label="Assessed start">{sourceText(scenario.mission_start)}</Fact>}
      {sourceText(scenario.mission_end) && <Fact label="Assessed end">{sourceText(scenario.mission_end)}</Fact>}
      {sourceText(scenario.scenario) && <Fact label="Scenario">{sourceText(scenario.scenario)}</Fact>}
      {Object.keys(msl).length > 0 && <Fact label="Compared zone limits">{sourceText(msl.lower) ?? 'Lower not supplied'} – {sourceText(msl.upper) ?? 'upper not supplied'} m MSL</Fact>}
    </dl>{Object.keys(scenario).length === 0 && <p>Assessed time and flight-height scope not supplied.</p>}
      {p.vertical_reference_assumption != null && <details><summary>Vertical comparison assumption</summary><AttributeList values={asRecord(p.vertical_reference_assumption)} /></details>}
    </SourceFacts>
    <SourceFacts title="Source record"><p className="source-identity">{item.source} · {item.id}</p><dl>
      {original.filter(key => sourceText(p[key]) != null).map(key => <Fact key={key} label={{ legal_ref: 'Legal reference', legal_reference: 'Legal reference', valid_from: 'Source valid from', valid_until: 'Source valid until', required_review: 'Required review' }[key] ?? key[0].toUpperCase() + key.slice(1)}>{sourceText(p[key])}</Fact>)}
      <HeightLimit properties={p} prefix="lower" /><HeightLimit properties={p} prefix="upper" />
    </dl>{originalOsm && <p><a href={`https://www.openstreetmap.org/${originalOsm[1]}/${originalOsm[2]}`} target="_blank" rel="noopener noreferrer">View original OSM {originalOsm[0]} ↗</a></p>}<p>Source limits and validity are distinct from the scenario assessment above. Missing limits do not mean zero height or unlimited applicability.</p></SourceFacts>
    <OriginalAttributes values={p} title="Assessment attributes" />
    {Object.keys(context).length > 0 && <details className="source-disclosure"><summary>Assessment provenance</summary><AttributeList values={context} /></details>}
  </>
}
