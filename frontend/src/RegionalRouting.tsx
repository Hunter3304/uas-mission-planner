import { useEffect, useRef, useState } from 'react'
import { postJson } from './api'
import CollapsiblePanel from './CollapsiblePanel'

interface RegionalResult {
  status: string
  message?: string
  length_m: number | null
  risk_length_cost: number | null
  objective_cost: number | null
  cruise_time_s: number | null
  cruise_time_range_s: [number, number] | null
  preparation_ms: number
  planner_ms: number
  endpoint_diagnostics: unknown
  research_assumptions: unknown[]
  geometry: unknown
}

export default function RegionalRouting({ datasetId }: { datasetId: string }) {
  const [controls, setControls] = useState({ start_id: 'rheuma-podbi', end_id: 'mhh', terrain_id: 'hannover-part2-terrain-v1',
    algorithm: 'astar', objective: 'risk', planning_mode: 'strict', cell_m: 250, background: '', time_budget_s: 3,
    risk_weight: 0.9, distance_weight: 0.1, agl_m: 100, speed_m_s: 30, clearance_m: 0, vertical_clearance_m: 0,
    mission_start: '', mission_end: '' })
  const [result, setResult] = useState<RegionalResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])
  function update(name: keyof typeof controls, value: string | number) {
    controller.current?.abort()
    setBusy(false)
    setResult(null)
    setError('')
    setControls(current => ({ ...current, [name]: value }))
  }
  async function solve() {
    controller.current?.abort()
    const active = new AbortController()
    controller.current = active
    setBusy(true)
    setResult(null)
    setError('')
    const { agl_m, speed_m_s, clearance_m, vertical_clearance_m, mission_start, mission_end, background, ...planner } = controls
    try {
      const response = await postJson<RegionalResult>(`/api/datasets/${encodeURIComponent(datasetId)}/study/route`, {
        ...planner, background_cost: background === '' ? null : Number(background),
        scenario: { agl_m, speed_m_s, clearance_m, vertical_clearance_m, mission_start, mission_end,
          scenario: 'civil', building_unknown_height: 'unresolved', zone_assessments: {} },
      }, active.signal)
      if (!active.signal.aborted) setResult(response)
    } catch (err) {
      if (!active.signal.aborted) setError(err instanceof Error ? err.message : 'Regional planning failed.')
    } finally {
      if (!active.signal.aborted) setBusy(false)
    }
  }
  function download() {
    if (!result) return
    const { geometry, ...metadata } = result
    const blob = new Blob([JSON.stringify({ type: 'FeatureCollection', metadata,
      features: result.status === 'success' ? [{ type: 'Feature', geometry, properties: { length_m: result.length_m } }] : [] }, null, 2)], { type: 'application/geo+json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${datasetId}-regional-route.geojson`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <CollapsiblePanel title="Regional route planning">
    <p>Use catalog location IDs. Enter scenario times with a UTC offset, for example 2026-10-07T10:00:00+02:00. These inputs do not establish flight permission.</p>
    <form onSubmit={event => { event.preventDefault(); void solve() }}>
      <div className="regional-controls">
        {(['start_id', 'end_id', 'terrain_id', 'mission_start', 'mission_end'] as const).map(name =>
          <label key={name}>{({ start_id: 'Origin ID', end_id: 'Destination ID', terrain_id: 'Terrain dataset', mission_start: 'Scenario start', mission_end: 'Scenario end' })[name]}
            <input required value={controls[name]} onChange={event => update(name, event.target.value)} /></label>)}
        {(['algorithm', 'objective', 'planning_mode'] as const).map(name =>
          <label key={name}>{name === 'planning_mode' ? 'Planning mode' : name === 'algorithm' ? 'Algorithm' : 'Objective'}
            <select aria-label={name === 'planning_mode' ? 'Planning mode' : name === 'algorithm' ? 'Algorithm' : 'Objective'} value={controls[name]} onChange={event => update(name, event.target.value)}>
              {(name === 'algorithm' ? ['astar', 'dijkstra', 'abitstar'] : name === 'objective' ? ['risk', 'distance'] : ['strict', 'research']).map(value => <option key={value} value={value}>{value}</option>)}
            </select></label>)}
        {([{ name: 'agl_m', label: 'Altitude AGL (m)', min: 100, max: 120 }, { name: 'speed_m_s', label: 'Cruise speed (m/s)', min: 25, max: 35 },
          { name: 'cell_m', label: 'Grid spacing (m)', min: 1 }, { name: 'clearance_m', label: 'Horizontal clearance (m)', min: 0, max: 1000 },
          { name: 'vertical_clearance_m', label: 'Vertical clearance (m)', min: 0, max: 1000 }, { name: 'time_budget_s', label: 'ABIT* budget (s)', min: 0, max: 60 },
          ...(controls.objective === 'risk' ? [{ name: 'risk_weight', label: 'Risk weight', min: 0 }, { name: 'distance_weight', label: 'Distance weight', min: 0 }] : [])
        ] as { name: keyof typeof controls; label: string; min: number; max?: number }[]).map(field =>
          <label key={field.name}>{field.label}<input type="number" required step="any" min={field.min} max={field.max} value={controls[field.name]} onChange={event => update(field.name, Number(event.target.value))} /></label>)}
        {controls.objective === 'risk' && <label>Background score assumption<input type="number" min="0" step="any" value={controls.background} placeholder="Unassessed" onChange={event => update('background', event.target.value)} /></label>}
      </div>
      <button disabled={busy}>{busy ? 'Preparing and planning…' : 'Plan regional route'}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {result && <div role="status">
      <p>{result.status}: {result.message}</p>
      {result.length_m !== null && <p>Length {result.length_m.toFixed(1)} m · Risk {result.risk_length_cost?.toFixed(2) ?? '—'} · Objective {result.objective_cost?.toFixed(2)} · Cruise {result.cruise_time_s?.toFixed(1)} s (25–35 m/s: {result.cruise_time_range_s?.map(t => t.toFixed(1)).join('–')} s)</p>}
      <p>Preparation {(result.preparation_ms / 1000).toFixed(2)} s · Search {(result.planner_ms / 1000).toFixed(2)} s</p>
      <details><summary>Constraint findings and assumptions</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify({ endpoints: result.endpoint_diagnostics, assumptions: result.research_assumptions }, null, 2)}</pre></details>
      <button onClick={download}>Export displayed result</button>
    </div>}
  </CollapsiblePanel>
}
