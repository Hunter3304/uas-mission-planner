import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Geometry } from 'geojson'
import RegionalMap, { type Study, type ConstraintLayers } from './RegionalMap'
import { getJson, postJson } from './api'
import CollapsiblePanel from './CollapsiblePanel'
import { berlinTimestamp, berlinDisplay, checkFlightTiming, type FlightTiming } from './scenarioTime'
import RestrictionProfiles, { type RestrictionReport } from './RestrictionProfiles'
import useScenarioLayers from './useScenarioLayers'
import { initialScenarioVisibility } from './regionalLayers'

const coordinateText = (value: number) => new Intl.NumberFormat('en', { maximumFractionDigits: 6, useGrouping: false }).format(value)

interface VerticalComparison {
  source: string
  aircraft_comparison_bounds_m: number[]
  zone_msl_bounds_m: { lower?: number; upper?: number }
  vertical_relation: string
  vertical_reference_assumption?: unknown
}
interface RegionalResult {
  timing?: FlightTiming
  status: string
  message?: string
  length_m: number | null
  risk_length_cost: number | null
  population_length_cost?: number | null
  population_active?: boolean
  population_assessment?: string
  population_model?: unknown
  effective_objective?: string
  effective_weights?: { building: number; distance: number; population: number }
  objective_cost: number | null
  cruise_time_s: number | null
  cruise_time_range_s: [number, number] | null
  preparation_ms: number
  planner_ms: number
  endpoint_diagnostics: Record<string, { vertical_comparisons?: VerticalComparison[] }>
  research_assumptions: unknown[]
  geometry: Geometry | null
  runtime_ms?: number
  source_preparation_ms?: number
  mission?: Record<string, unknown>
  provenance?: unknown
  controls?: unknown
  restriction_report?: RestrictionReport
}

export default function RegionalRouting({ datasetId }: { datasetId: string }) {
  const [controls, setControls] = useState({ start_id: 'rheuma-podbi', end_id: 'mhh', terrain_id: 'hannover-part2-terrain-v1',
    algorithm: 'astar', objective: 'risk', planning_mode: 'conservative', profile_id: '', cell_m: 250, background: '', time_budget_s: 3,
    risk_weight: 0.9, distance_weight: 0.1, include_population: false, population_weight: '1', agl_m: 100, speed_m_s: 30, clearance_m: 0, vertical_clearance_m: 0,
    mission_start: '', research_height_m: 30, corridor_margin_m: 1000,
    vertical_reference_policy: 'nhn_as_msl_assumption', nhn_msl_offset_m: 0, nhn_msl_uncertainty_m: 0 })
  const [terrains, setTerrains] = useState<{ id: string; tiles: number }[]>([])
  const [terrainError, setTerrainError] = useState('')
  const [override, setOverride] = useState({ enabled: false, start_lon: '', start_lat: '', end_lon: '', end_lat: '' })
  const [result, setResult] = useState<RegionalResult | null>(null)
  const [study, setStudy] = useState<Study | null>(null)
  const [studyError, setStudyError] = useState('')
  const [layerVisibility, setLayerVisibility] = useState(initialScenarioVisibility)
  useEffect(() => {
    const active = new AbortController()
    getJson<{ datasets: { id: string; tiles: number }[] }>('/api/terrain-datasets', active.signal)
      .then(value => { if (!active.signal.aborted) setTerrains(value.datasets ?? []) })
      .catch(error => { if (!active.signal.aborted) setTerrainError(error.message) })
    getJson<Study>(`/api/datasets/${encodeURIComponent(datasetId)}/study?catalog_only=true`, active.signal)
      .then(value => { if (!active.signal.aborted) setStudy(value) })
      .catch(error => { if (!active.signal.aborted) setStudyError(error.message) })
    return () => { active.abort() }
  }, [datasetId])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  function scenario() {
    const { agl_m, speed_m_s, clearance_m, vertical_clearance_m, mission_start } = controls
    return { agl_m, speed_m_s, clearance_m, vertical_clearance_m, mission_start: berlinTimestamp(mission_start), scenario: 'civil', timezone: 'Europe/Berlin', building_unknown_height: 'unresolved', zone_assessments: {},
      ...(controls.planning_mode !== 'strict' ? { research_geometry: 'derived', research_height_m: controls.research_height_m, research_geometry_buffer_m: 20,
        vertical_reference_policy: controls.vertical_reference_policy, nhn_msl_offset_m: controls.nhn_msl_offset_m, nhn_msl_uncertainty_m: controls.nhn_msl_uncertainty_m } : {}) }
  }
  function coordinate(name: 'start' | 'end'): [number, number] {
    if (!study) throw new Error('Wait for the study bounds and saved sites to load.')
    const b = study.config.bounds
    return (['lon', 'lat'] as const).map(axis => {
      const text = override[`${name}_${axis}`]
      const value = Number(text)
      const min = axis === 'lon' ? b.west : b.south
      const max = axis === 'lon' ? b.east : b.north
      const label = `${name === 'start' ? 'Start' : 'End'} ${axis === 'lon' ? 'longitude' : 'latitude'}`
      if (!text.trim() || !Number.isFinite(value)) throw new Error(`Enter ${label.toLowerCase()} in decimal degrees.`)
      if (value < min || value > max) throw new Error(`${label} must be within the study range ${min} to ${max}°.`)
      return value
    }) as [number, number]
  }
  let pendingReason = ''
  let layerKey = ''
  let activeStart: [number, number] | undefined
  let activeEnd: [number, number] | undefined
  try {
    if (!study) throw new Error('Waiting for the study bounds and saved sites.')
    if (override.enabled) { activeStart = coordinate('start'); activeEnd = coordinate('end') }
    else {
      const start = study.config.locations.find(site => site.id === controls.start_id)
      const end = study.config.locations.find(site => site.id === controls.end_id)
      if (!start || !end) throw new Error('Choose an origin and destination from the saved sites.')
      activeStart = [start.longitude, start.latitude]; activeEnd = [end.longitude, end.latitude]
    }
    if (!controls.mission_start) throw new Error('Enter a departure time in the planning panel.')
    if (!terrains.some(terrain => terrain.id === controls.terrain_id)) throw new Error('Choose an available terrain dataset in the planning panel.')
    if (![controls.agl_m, controls.speed_m_s, controls.clearance_m, controls.vertical_clearance_m, controls.research_height_m, controls.nhn_msl_offset_m, controls.nhn_msl_uncertainty_m].every(Number.isFinite)) throw new Error('Complete the scenario height, speed and clearance inputs.')
    if (controls.agl_m < 100 || controls.agl_m > 120 || controls.speed_m_s < 25 || controls.speed_m_s > 35 || controls.clearance_m < 0 || controls.vertical_clearance_m < 0) throw new Error('Check the scenario altitude, speed and clearance ranges.')
    layerKey = JSON.stringify({ duration_mode: result?.status === 'success' ? 'explicit' : 'automatic', start_id: controls.start_id, end_id: controls.end_id, ...(override.enabled ? { start_coordinate: activeStart, end_coordinate: activeEnd } : {}), scenario: { ...scenario(), ...(result?.status === 'success' ? result.timing?.assessed_interval : {}) }, terrain_id: controls.terrain_id, profile_id: controls.profile_id || undefined, planning_mode: controls.planning_mode })
  } catch (failure) { pendingReason = failure instanceof Error ? failure.message : 'Complete the scenario inputs.' }
  const layers = useScenarioLayers(datasetId, layerKey, Object.values(layerVisibility).some(Boolean) && !busy)
  const constraints: ConstraintLayers | null = layers.data
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])
  function update(name: keyof typeof controls, value: string | number | boolean) {
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
    try {
      if (controls.include_population && (!controls.population_weight.trim() || !Number.isFinite(Number(controls.population_weight)) || Number(controls.population_weight) < 0))
        throw new Error('Enter a finite, nonnegative population weight.')
      await layers.waitForIdle()
      if (active.signal.aborted) return
      const requestedScenario = scenario()
      const response = await postJson<RegionalResult>(`/api/datasets/${encodeURIComponent(datasetId)}/study/route`, {
        duration_mode: 'automatic', start_id: controls.start_id, end_id: controls.end_id, terrain_id: controls.terrain_id,
        algorithm: controls.algorithm, objective: controls.objective, planning_mode: controls.planning_mode,
        profile_id: controls.profile_id || undefined,
        cell_m: controls.cell_m, time_budget_s: controls.time_budget_s, corridor_margin_m: controls.corridor_margin_m,
        risk_weight: controls.risk_weight, distance_weight: controls.distance_weight,
        include_population: controls.include_population,
        ...(controls.include_population ? { population_weight: Number(controls.population_weight) } : {}),
        background_cost: controls.background === '' ? null : Number(controls.background), scenario: requestedScenario,
        ...(override.enabled ? { start_coordinate: coordinate('start'), end_coordinate: coordinate('end') } : {}),
      }, active.signal)
      if (!active.signal.aborted) {
        if (response.status === 'success') {
          checkFlightTiming(response.timing, requestedScenario.mission_start, response.length_m, controls.speed_m_s)
          if (response.mission?.mission_start !== requestedScenario.mission_start || response.mission?.mission_end !== response.timing?.estimated_arrival)
            throw new Error('The returned mission interval does not match its flight estimate. Plan again.')
        }
        setResult(response)
      }
    } catch (err) {
      if (!active.signal.aborted) setError(err instanceof Error ? err.message : 'Regional planning failed.')
    } finally {
      if (!active.signal.aborted) setBusy(false)
    }
  }
  function download() {
    if (!result) return
    const { geometry, ...resultMetadata } = result
    const metadata = { ...resultMetadata, displayed_controls: controls, displayed_endpoint_selection: override, catalog_endpoints: study?.config.locations.filter(site => site.id === controls.start_id || site.id === controls.end_id) }
    const blob = new Blob([JSON.stringify({ type: 'FeatureCollection', metadata,
      features: result.status === 'success' ? [{ type: 'Feature', geometry, properties: {
        length_m: result.length_m, risk_length_cost: result.risk_length_cost,
        population_length_cost: result.population_length_cost ?? null, objective_cost: result.objective_cost,
        effective_objective: result.effective_objective, effective_weights: result.effective_weights,
      } }] : [] }, null, 2)], { type: 'application/geo+json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${datasetId}-regional-route.geojson`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const mapTarget = document.getElementById('regional-map')
  const assessedInterval = result?.status === 'success' ? result.timing?.assessed_interval : constraints?.flight_interval?.assessed_interval
  return <CollapsiblePanel title="Regional route planning">
    {mapTarget && createPortal(<RegionalMap datasetId={datasetId} study={study} startId={controls.start_id} endId={controls.end_id} startCoordinate={activeStart} endCoordinate={activeEnd} exactCoordinates={override.enabled} geometry={result?.status === 'success' ? result.geometry : null} constraints={constraints} layerVisibility={layerVisibility} onLayerVisibility={setLayerVisibility} layerState={{ pendingReason, loading: layers.loading, error: layers.error, retry: layers.retry }} />, mapTarget)}
    {studyError && <p role="alert">Location catalog: {studyError}</p>}
    <p>Select endpoints and departure in Europe/Berlin. Estimated arrival uses the successful route length divided by cruise speed, with no takeoff/landing allowance. Addresses are not verified launch or landing sites.</p>
    {terrainError && <p role="alert">Terrain catalog: {terrainError}</p>}
    <form onSubmit={event => { event.preventDefault(); void solve() }}>
      <fieldset className="endpoint-section">
        <legend>Origin and destination</legend>
        <div className={`endpoint-row ${override.enabled ? 'endpoint-row-exact' : ''}`}>
          <label>Selection method
            <select value={override.enabled ? 'coordinates' : 'sites'} onChange={event => {
              update('start_id', controls.start_id)
              setOverride(current => ({ ...current, enabled: event.target.value === 'coordinates' }))
            }}>
              <option value="sites">Choose from saved sites</option>
              <option value="coordinates">Enter exact coordinates</option>
            </select>
          </label>
          {!override.enabled && (['start_id', 'end_id'] as const).map(name => <label key={name}>{name === 'start_id' ? 'Origin' : 'Destination'}<select aria-label={name === 'start_id' ? 'Origin' : 'Destination'} required value={controls[name]} disabled={!study} onChange={event => update(name, event.target.value)}>{study?.config.locations.map(site => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label>)}
          {override.enabled && (['start_lon', 'start_lat', 'end_lon', 'end_lat'] as const).map(name => {
            const b = study?.config.bounds
            const min = name.endsWith('lon') ? b?.west : b?.south
            const max = name.endsWith('lon') ? b?.east : b?.north
            const value = override[name]
            const invalid = value.trim() !== '' && (!Number.isFinite(Number(value)) || (min != null && Number(value) < min) || (max != null && Number(value) > max))
            const label = { start_lon: 'Start longitude', start_lat: 'Start latitude', end_lon: 'End longitude', end_lat: 'End latitude' }[name]
            return <label key={name}>{label} (decimal degrees)
              <input required type="number" step="any" min={min} max={max} disabled={!b} value={value} aria-invalid={invalid} aria-describedby={invalid ? `${name}-error` : 'endpoint-bounds'} onChange={event => {
                update('start_id', controls.start_id)
                setOverride(current => ({ ...current, [name]: event.target.value }))
              }} />
              {invalid && <small id={`${name}-error`} className="field-error">{label} must be between {min == null ? '—' : coordinateText(min)} and {max == null ? '—' : coordinateText(max)}°.</small>}
            </label>
          })}
        </div>
        {override.enabled && <p id="endpoint-bounds" className="endpoint-bounds">{study ? `Study bounds (WGS84 decimal degrees, approximate): longitude ${coordinateText(study.config.bounds.west)} to ${coordinateText(study.config.bounds.east)}°; latitude ${coordinateText(study.config.bounds.south)} to ${coordinateText(study.config.bounds.north)}°. Inputs retain full precision; points still require endpoint constraint checks.` : 'Waiting for the study coordinate bounds…'}</p>}
      </fieldset>
      <h4 className="planning-parameters-heading">Flight and planning parameters</h4>
      <div className="regional-controls">
        <label>Terrain dataset<select required value={controls.terrain_id} onChange={event => update('terrain_id', event.target.value)}>
          {!terrains.some(t => t.id === controls.terrain_id) && <option value={controls.terrain_id}>{controls.terrain_id} — awaiting catalog</option>}
          {terrains.map(t => <option key={t.id} value={t.id}>{t.id} ({t.tiles} tiles)</option>)}
        </select></label>
<label>Departure time<input type="datetime-local" required step="1" value={controls.mission_start} onChange={event => update('mission_start', event.target.value)} /></label>
        {(['algorithm', 'objective', 'planning_mode'] as const).map(name => {
          const label = name === 'planning_mode' ? 'Planning mode' : name === 'algorithm' ? 'Algorithm' : 'Objective'
          const select = <label key={name}>{label}
            <select aria-label={label} value={controls[name]} onChange={event => update(name, event.target.value)}>
              {(name === 'algorithm' ? ['astar', 'dijkstra', 'abitstar'] : name === 'objective' ? ['risk', 'distance'] : ['conservative', 'strict', 'research']).map(value => <option key={value} value={value}>{value}</option>)}
            </select></label>
          return name === 'objective' ? <div key={name} className="route-objective-controls">
            {select}
            <label className="population-routing-toggle"><input type="checkbox" checked={controls.include_population} onChange={event => update('include_population', event.target.checked)} />Include population</label>
            {controls.include_population && <>
              <label>Population weight<input type="number" required min="0" step="any" value={controls.population_weight} onChange={event => update('population_weight', event.target.value)} aria-describedby="population-objective-help" /></label>
              <small id="population-objective-help">{controls.objective === 'distance' ? 'Distance + population: length + weight × population cost.' : 'Building risk + population: building weight × building cost + distance weight × length + population weight × population cost.'} Population cost sums distance within each 250 m cell × its class (0–4). Weight 0 disables this contribution.</small>
            </>}
          </div> : select
        })}
        {([{ name: 'agl_m', label: 'Altitude AGL (m)', min: 100, max: 120 }, { name: 'speed_m_s', label: 'Cruise speed (m/s)', min: 25, max: 35 },
          { name: 'cell_m', label: 'Grid spacing (m)', min: 1 }, { name: 'clearance_m', label: 'Horizontal clearance (m)', min: 0, max: 1000 },
          { name: 'vertical_clearance_m', label: 'Vertical clearance (m)', min: 0, max: 1000 }, { name: 'time_budget_s', label: 'Search budget (s)', min: 0, max: 60 },
          { name: 'corridor_margin_m', label: 'Initial corridor margin (m)', min: 100, max: 10000 },
          ...(controls.planning_mode !== 'strict' ? [{ name: 'research_height_m', label: 'Missing building height estimate (m)', min: 0, max: 1000 }] : []),
          ...(controls.planning_mode !== 'strict' && controls.vertical_reference_policy === 'nhn_as_msl_assumption' ? [
            { name: 'nhn_msl_offset_m', label: 'NHN to MSL offset (m)', min: -1000, max: 1000 },
            { name: 'nhn_msl_uncertainty_m', label: 'NHN to MSL uncertainty (m)', min: 0, max: 1000 }] : []),
          ...(controls.objective === 'risk' ? [{ name: 'risk_weight', label: 'Risk weight', min: 0 }, { name: 'distance_weight', label: 'Distance weight', min: 0 }] : [])
        ] as { name: keyof typeof controls; label: string; min: number; max?: number }[]).map(field =>
          <label key={field.name}>{field.label}<input type="number" required step="any" min={field.min} max={field.max} value={String(controls[field.name])} onChange={event => update(field.name, Number(event.target.value))} /></label>)}
        {controls.objective === 'risk' && <label>Background score assumption<input type="number" min="0" step="any" value={controls.background} placeholder="Unassessed" onChange={event => update('background', event.target.value)} /></label>}
      </div>
      <label><input type="checkbox" checked={controls.planning_mode !== 'strict' && controls.vertical_reference_policy === 'nhn_as_msl_assumption'} disabled={controls.planning_mode === 'strict'} onChange={event => update('vertical_reference_policy', event.target.checked ? 'nhn_as_msl_assumption' : 'source')} />Compare MSL zones using NHN + AGL (engineering assumption)</label>
      {controls.planning_mode !== 'strict' && controls.vertical_reference_policy === 'nhn_as_msl_assumption' && <p>Comparison height = NHN ground height + AGL + offset. Uncertainty expands both bounds; default offset/uncertainty 0 m is an explicit approximation. Original datums remain unchanged. Whole-motion terrain bounds are checked; overlap still requires zone conditions or permission. Strict mode requires verified reference compatibility.</p>}
      {controls.planning_mode === 'research' && <p>Research route: derived polygon repairs; uncertain non-polygon extents excluded with a 20 m buffer; missing heights use the explicit estimate above. Zone applicability, NHN/MSL compatibility and temporary restrictions remain assumptions. Known obstacles and missing terrain remain excluded. For the weighted objective, enter an explicit background score assumption, such as 0.</p>}
      {controls.planning_mode === 'conservative' && <p>Conservative avoidance excludes unresolved zone footprints and confirmed prohibitions. Building geometry repairs and missing-height estimates remain explicit engineering assumptions. Temporary/NOTAM coverage is unverified; a successful candidate is not flight permission.</p>}
      {!override.enabled && controls.start_id === controls.end_id && <p>Origin and destination are the same address. A zero-length route still requires endpoint constraint validation.</p>}
      <button disabled={busy || !study}>{busy ? 'Preparing and planning…' : 'Plan regional route'}</button>
    </form>
    <section className="flight-estimate source-card" aria-label="Flight time estimate"><h4>Estimated arrival</h4>{result?.status === 'success' && result.timing?.estimated_arrival ? <><p className="source-main-value">{berlinDisplay(result.timing.estimated_arrival)}</p><p>{result.length_m?.toFixed(1)} m ÷ {controls.speed_m_s} m/s = {result.timing.cruise_time_s?.toFixed(3)} s of cruise. Cruise only; planning computation time is separate.</p><p>Assessed interval: {berlinDisplay(result.timing.assessed_interval.mission_start)} — {berlinDisplay(result.timing.assessed_interval.mission_end)}</p></> : <p>Awaiting route</p>}</section>
    <p className="layer-help" data-testid="flight-interval-scope" data-assessed-start={assessedInterval?.mission_start} data-assessed-end={assessedInterval?.mission_end}>{result?.status === 'success' ? 'Completed route assessment: enabled layers refresh automatically to the returned assessed interval.' : 'Provisional preview: layers use a straight-line duration seed, not a successful route ETA. The actual flight interval is checked after planning.'}{assessedInterval && <> Inspection interval: {berlinDisplay(assessedInterval.mission_start)} — {berlinDisplay(assessedInterval.mission_end)}.</>}</p>
    <RestrictionProfiles datasetId={datasetId} report={result?.restriction_report ?? constraints?.restriction_report} interval={assessedInterval} intervalLabel={result?.status === 'success' ? 'Completed route assessment interval' : 'Provisional preview interval'} onSelect={id => update('profile_id', id)} />
    {error && <p role="alert">{error}</p>}
    {result && <div role="status">
      <p>{result.status}: {result.message}</p>
      {Object.entries(result.endpoint_diagnostics ?? {}).flatMap(([endpoint, diagnostics]) => (diagnostics.vertical_comparisons ?? []).map((comparison, index) =>
        <p key={`${endpoint}-${comparison.source}-${index}`} style={{ overflowWrap: 'anywhere' }}>
          {endpoint} · {comparison.source}: aircraft {comparison.aircraft_comparison_bounds_m.map(v => v.toFixed(3)).join('–')} m MSL comparison · zone {comparison.zone_msl_bounds_m.lower?.toFixed(3) ?? 'unbounded'}–{comparison.zone_msl_bounds_m.upper?.toFixed(3) ?? 'unbounded'} m MSL · {comparison.vertical_relation} {comparison.vertical_reference_assumption ? '(NHN + AGL engineering assumption)' : '(source reference)'}.
        </p>))}
      {result.restriction_report && <p>Zone decisions: {Object.entries(result.restriction_report.counts).map(([key, count]) => `${key}: ${count}`).join(' · ')}. Coverage: {result.restriction_report.coverage.status} — {result.restriction_report.coverage.reason}</p>}
      {result.status === 'unresolved_input' && <p>Review the findings below. Research mode requires explicit geometry and height assumptions; weighted routing also needs an assessed background score. Missing terrain cannot be bypassed.</p>}
      {result.status === 'invalid_endpoint' && <p>The selected point conflicts with a constraint. Review its source below and explicitly choose another launch/landing point if appropriate.</p>}
      {result.length_m !== null && <section aria-label="Route costs">
        <p>Length {result.length_m.toFixed(1)} m</p>
        {result.risk_length_cost != null && <p>Building cost {result.risk_length_cost.toFixed(2)} score-metres</p>}
        {result.population_active && result.population_length_cost != null && <p>Population cost {result.population_length_cost.toFixed(2)} score-metres</p>}
        <p>Objective cost {result.objective_cost?.toFixed(2)}</p>
        <p>Cruise {result.cruise_time_s?.toFixed(1)} s (25–35 m/s: {result.cruise_time_range_s?.map(t => t.toFixed(1)).join('–')} s)</p>
      </section>}
      <p>Altitude {controls.agl_m} m AGL · Speed {controls.speed_m_s} m/s · {controls.algorithm} · {result.effective_objective === 'distance+population' ? 'Distance + population' : result.effective_objective === 'risk+population' ? 'Building risk + population' : result.effective_objective ?? controls.objective} · {controls.planning_mode}</p>
      {result.effective_weights && <p>Effective weights: building {result.effective_weights.building} · distance {result.effective_weights.distance} · population {result.effective_weights.population}</p>}
      {result.population_assessment && <p>Population assessment: {result.population_assessment === 'not_evaluated' ? 'Not evaluated (inactive)' : result.population_assessment}</p>}
      <p>Preparation {(result.preparation_ms / 1000).toFixed(2)} s · Search {(result.planner_ms / 1000).toFixed(2)} s · Total {result.runtime_ms == null ? '—' : (result.runtime_ms / 1000).toFixed(2)} s · Source preparation {result.source_preparation_ms == null ? '—' : (result.source_preparation_ms / 1000).toFixed(2)} s</p>
      <p>Time estimates cover constant cruise only; takeoff, landing, wind and dynamics are excluded.</p>
      <details open><summary>Constraint findings and assumptions</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '22rem', overflow: 'auto' }}>{JSON.stringify({ endpoints: result.endpoint_diagnostics, assumptions: result.research_assumptions }, null, 2)}</pre></details>
      {result.population_model != null && <details><summary>Population model and classification</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '22rem', overflow: 'auto' }}>{JSON.stringify(result.population_model, null, 2)}</pre></details>}
      <button onClick={download}>Export displayed result</button>
    </div>}
  </CollapsiblePanel>
}
