import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Geometry } from 'geojson'
import RegionalMap, { type Study, type ConstraintLayers } from './RegionalMap'
import { getJson, postJson } from './api'
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
  geometry: Geometry | null
  runtime_ms?: number
  source_preparation_ms?: number
  mission?: Record<string, unknown>
  provenance?: unknown
  controls?: unknown
}

export default function RegionalRouting({ datasetId }: { datasetId: string }) {
  const [controls, setControls] = useState({ start_id: 'rheuma-podbi', end_id: 'mhh', terrain_id: 'hannover-part2-terrain-v1',
    algorithm: 'astar', objective: 'risk', planning_mode: 'strict', cell_m: 250, background: '', time_budget_s: 3,
    risk_weight: 0.9, distance_weight: 0.1, agl_m: 100, speed_m_s: 30, clearance_m: 0, vertical_clearance_m: 0,
    mission_start: '', mission_end: '' })
  const [result, setResult] = useState<RegionalResult | null>(null)
  const [study, setStudy] = useState<Study | null>(null)
  const [studyError, setStudyError] = useState('')
  const [constraints, setConstraints] = useState<ConstraintLayers | null>(null)
  const [layerBusy, setLayerBusy] = useState(false)
  const layerController = useRef<AbortController | null>(null)
  useEffect(() => {
    const active = new AbortController()
    getJson<Study>(`/api/datasets/${encodeURIComponent(datasetId)}/study`, active.signal)
      .then(value => { if (!active.signal.aborted) setStudy(value) })
      .catch(error => { if (!active.signal.aborted) setStudyError(error.message) })
    return () => { active.abort(); layerController.current?.abort() }
  }, [datasetId])
  function scenario() {
    const { agl_m, speed_m_s, clearance_m, vertical_clearance_m, mission_start, mission_end } = controls
    return { agl_m, speed_m_s, clearance_m, vertical_clearance_m, mission_start, mission_end, scenario: 'civil', building_unknown_height: 'unresolved', zone_assessments: {} }
  }
  async function loadConstraints() {
    layerController.current?.abort()
    const active = new AbortController()
    layerController.current = active
    setLayerBusy(true); setError('')
    try {
      const response = await postJson<ConstraintLayers>(`/api/datasets/${encodeURIComponent(datasetId)}/study/layers/constraints`, { scenario: scenario(), terrain_id: controls.terrain_id }, active.signal)
      if (!active.signal.aborted) setConstraints(response)
    } catch (error) { if (!active.signal.aborted) setError(error instanceof Error ? error.message : 'Cannot load constraints.') }
    finally { if (!active.signal.aborted) setLayerBusy(false) }
  }
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])
  function update(name: keyof typeof controls, value: string | number) {
    controller.current?.abort()
    setBusy(false)
    setResult(null)
    if (['agl_m', 'clearance_m', 'vertical_clearance_m', 'mission_start', 'mission_end', 'terrain_id'].includes(name)) {
      layerController.current?.abort(); setConstraints(null); setLayerBusy(false)
    }
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
    const { geometry, ...resultMetadata } = result
    const metadata = { ...resultMetadata, displayed_controls: controls, catalog_endpoints: study?.config.locations.filter(site => site.id === controls.start_id || site.id === controls.end_id) }
    const blob = new Blob([JSON.stringify({ type: 'FeatureCollection', metadata,
      features: result.status === 'success' ? [{ type: 'Feature', geometry, properties: { length_m: result.length_m } }] : [] }, null, 2)], { type: 'application/geo+json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${datasetId}-regional-route.geojson`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const mapTarget = document.getElementById('regional-map')
  return <CollapsiblePanel title="Regional route planning">
    {mapTarget && createPortal(<RegionalMap datasetId={datasetId} study={study} startId={controls.start_id} endId={controls.end_id} geometry={result?.status === 'success' ? result.geometry : null} constraints={constraints} />, mapTarget)}
    {studyError && <p role="alert">Location catalog: {studyError}</p>}
    <p>Select verified catalog addresses. Addresses are not verified launch or landing sites. Enter scenario times with a UTC offset, for example 2026-10-07T10:00:00+02:00. These inputs do not establish flight permission.</p>
    <form onSubmit={event => { event.preventDefault(); void solve() }}>
      <div className="regional-controls">
        {(['start_id', 'end_id'] as const).map(name => <label key={name}>{name === 'start_id' ? 'Origin' : 'Destination'}<select aria-label={name === 'start_id' ? 'Origin' : 'Destination'} required value={controls[name]} disabled={!study} onChange={event => update(name, event.target.value)}>{study?.config.locations.map(site => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label>)}
        {(['terrain_id', 'mission_start', 'mission_end'] as const).map(name =>
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
      {controls.start_id === controls.end_id && <p>Origin and destination are the same address. A zero-length route still requires endpoint constraint validation.</p>}
      <button type="button" disabled={layerBusy || !controls.mission_start || !controls.mission_end} onClick={() => void loadConstraints()}>{layerBusy ? 'Preparing scenario layers…' : 'Load scenario layers'}</button>
      <button disabled={busy || !study}>{busy ? 'Preparing and planning…' : 'Plan regional route'}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {result && <div role="status">
      <p>{result.status}: {result.message}</p>
      {result.length_m !== null && <p>Length {result.length_m.toFixed(1)} m · Risk {result.risk_length_cost?.toFixed(2) ?? '—'} · Objective {result.objective_cost?.toFixed(2)} · Cruise {result.cruise_time_s?.toFixed(1)} s (25–35 m/s: {result.cruise_time_range_s?.map(t => t.toFixed(1)).join('–')} s)</p>}
      <p>Altitude {controls.agl_m} m AGL · Speed {controls.speed_m_s} m/s · {controls.algorithm} · {controls.objective} ({controls.objective === 'risk' ? `${controls.risk_weight}/${controls.distance_weight}` : 'distance only'}) · {controls.planning_mode}</p>
      <p>Preparation {(result.preparation_ms / 1000).toFixed(2)} s · Search {(result.planner_ms / 1000).toFixed(2)} s · Total {result.runtime_ms == null ? '—' : (result.runtime_ms / 1000).toFixed(2)} s · Source preparation {result.source_preparation_ms == null ? '—' : (result.source_preparation_ms / 1000).toFixed(2)} s</p>
      <p>Time estimates cover constant cruise only; takeoff, landing, wind and dynamics are excluded.</p>
      <details><summary>Constraint findings and assumptions</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify({ endpoints: result.endpoint_diagnostics, assumptions: result.research_assumptions }, null, 2)}</pre></details>
      <button onClick={download}>Export displayed result</button>
    </div>}
  </CollapsiblePanel>
}
