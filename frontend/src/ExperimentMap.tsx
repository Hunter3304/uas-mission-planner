import { useCallback, useEffect, useRef, useState } from 'react'
import type { FeatureCollection } from 'geojson'
import { getJson } from './api'
import { populationColor, type ExternalFeature, type Experiment, type GridData, type GridCell, type RouteResult, type ComparisonReport } from './external'
import MapCanvas, { type Props as MapProps } from './MapCanvas'

interface Location {
  longitude: number
  latitude: number
  agl_m: number
  terrain_m: number | null
  aircraft_altitude_m: number | null
  vertical_datum: string
  people_per_cell: number | null
  zones: ExternalFeature[]
}
const number = (value: number | null | undefined) =>
  value == null ? 'Unknown / NoData' : value.toFixed(3)
const routeLabels: Record<string, string> = {
  success: 'Route found', invalid_endpoint: 'Invalid endpoint',
  unresolved_input: 'Unresolved input', no_path_on_grid: 'No path on this grid',
  planner_unavailable: 'Planner unavailable', timeout: 'Timed out without exact route',
  approximate_solution: 'Approximate candidate only', cancelled: 'Cancelled',
  resource_limit: 'Search limit reached', computational_failure: 'Route validation failed',
}

export default function ExperimentMap(props: MapProps) {
  const [snapshot, setSnapshot] = useState<{
    experiment: Experiment
    population: FeatureCollection
    zones: FeatureCollection
  } | null>(null)
  const [error, setError] = useState('')
  const [showPopulation, setShowPopulation] = useState(true)
  const [showZones, setShowZones] = useState(false)
  const [selected, setSelected] = useState<ExternalFeature | null>(null)
  const [location, setLocation] = useState<Location | null>(null)
  const [point, setPoint] = useState<[number, number] | null>(null)
  const [inspecting, setInspecting] = useState(false)
  const [pointError, setPointError] = useState('')
  const [cellSize, setCellSize] = useState(50)
  const [grid, setGrid] = useState<GridData | null>(null)
  const [gridError, setGridError] = useState('')
  const [showGrid, setShowGrid] = useState(false)
  const [selectedCell, setSelectedCell] = useState<GridCell | null>(null)
  const [endpoints, setEndpoints] = useState<{ start: [number, number]; end: [number, number] } | null>(null)
  const [selection, setSelection] = useState<'inspect' | 'start' | 'end'>('inspect')
  const [route, setRoute] = useState<RouteResult | null>(null)
  const [routeError, setRouteError] = useState('')
  const [routing, setRouting] = useState(false)
  const [algorithm, setAlgorithm] = useState('astar')
  const [objective, setObjective] = useState('distance')
  const [riskWeight, setRiskWeight] = useState(0.9)
  const [distanceWeight, setDistanceWeight] = useState(0.1)
  const [backgroundCost, setBackgroundCost] = useState('')
  const [safetyDistance, setSafetyDistance] = useState(0)
  const [budget, setBudget] = useState(3)
  const [repetitions, setRepetitions] = useState(3)
  const [comparison, setComparison] = useState<ComparisonReport | null>(null)
  const [comparing, setComparing] = useState(false)
  const comparisonController = useRef<AbortController | null>(null)
  const [showReference, setShowReference] = useState(false)
  const routeController = useRef<AbortController | null>(null)
  const base = `/api/datasets/${encodeURIComponent(props.dataset.id)}/experiment`
  useEffect(() => {
    const controller = new AbortController()
    setSnapshot(null)
    setError('')
    setSelected(null)
    setLocation(null)
    setPoint(null)
    setInspecting(false)
    setPointError('')
    setGrid(null)
    setSelectedCell(null)
    setEndpoints(null)
    setRoute(null)
    setRouteError('')
    setSelection('inspect')
    if (props.dataset.has_experiment) {
      Promise.all([
        getJson<Experiment>(base, controller.signal),
        getJson<FeatureCollection>(`${base}/layers/population`, controller.signal),
        getJson<FeatureCollection>(`${base}/layers/zones`, controller.signal),
      ])
        .then(([experiment, population, zones]) => {
          setSnapshot({ experiment, population, zones })
          setEndpoints({ start: experiment.config.start, end: experiment.config.end })
        })
        .catch((err) => {
          if (!controller.signal.aborted) setError(err.message)
        })
    }
    return () => controller.abort()
  }, [base, props.dataset])
  useEffect(() => {
    if (!snapshot) return
    const controller = new AbortController()
    setGrid(null)
    setSelectedCell(null)
    setGridError('')
    if (!Number.isFinite(cellSize) || cellSize <= 0) {
      setGridError('Grid cell size must be positive.')
      return
    }
    getJson<GridData>(`${base}/grid?cell_m=${cellSize}`, controller.signal)
      .then((result) => { if (!controller.signal.aborted) setGrid(result) })
      .catch((err) => { if (!controller.signal.aborted) setGridError(err.message) })
    return () => controller.abort()
  }, [base, snapshot, cellSize])
  useEffect(() => {
    if (!point || !snapshot) return
    const controller = new AbortController()
    setInspecting(true)
    setPointError('')
    setLocation(null)
    getJson<Location>(
      `${base}/inspect?longitude=${point[0]}&latitude=${point[1]}`,
      controller.signal,
    )
      .then(setLocation)
      .catch((err) => {
        if (!controller.signal.aborted) setPointError(err.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setInspecting(false)
      })
    return () => controller.abort()
  }, [base, point, snapshot])
  useEffect(() => {
    routeController.current?.abort()
    setRoute(null)
    setRouteError('')
    setRouting(false)
    comparisonController.current?.abort()
    setComparison(null)
    setComparing(false)
    return () => { routeController.current?.abort(); comparisonController.current?.abort() }
  }, [base, cellSize, endpoints, algorithm, objective, riskWeight, distanceWeight, backgroundCost, safetyDistance, budget, repetitions])
  const onLocation = useCallback((lon: number, lat: number) => {
    if (selection === 'inspect') setPoint([lon, lat])
    else {
      setEndpoints((previous) => previous ? { ...previous, [selection]: [lon, lat] } : previous)
      setSelection('inspect')
    }
  }, [selection])
  const controlQuery = () => ({
    cell_m: String(cellSize), algorithm, objective, risk_weight: String(riskWeight),
    distance_weight: String(distanceWeight), safety_distance_m: String(safetyDistance),
    time_budget_s: String(budget), ...(backgroundCost === '' ? {} : { background_cost: backgroundCost }),
  })
  const routeQuery = () => new URLSearchParams({
    ...controlQuery(),
    cell_m: String(cellSize), start_lon: String(endpoints!.start[0]), start_lat: String(endpoints!.start[1]),
    end_lon: String(endpoints!.end[0]), end_lat: String(endpoints!.end[1]),
  })
  const generateRoute = async () => {
    routeController.current?.abort()
    const controller = new AbortController()
    routeController.current = controller
    setRouting(true)
    setRoute(null)
    setRouteError('')
    try {
      const result = await getJson<RouteResult>(`${base}/route?${routeQuery()}`, controller.signal)
      if (!controller.signal.aborted) setRoute(result)
    } catch (err) {
      if (!controller.signal.aborted) setRouteError((err as Error).message)
    } finally {
      if (!controller.signal.aborted) setRouting(false)
    }
  }
  const download = (value: unknown, filename: string, type: string) => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type }))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const exportRoute = () => {
    if (!route) return
    const { geometry, ...metadata } = route
    download({ type: 'FeatureCollection', metadata, features: route.status === 'success'
      ? [{ type: 'Feature', geometry, properties: { length_m: route.length_m,
        risk_length_cost: route.risk_length_cost, objective_cost: route.objective_cost,
        rules_version: route.rules_version } }] : [] }, `${props.dataset.id}-route.geojson`, 'application/geo+json')
  }
  const compareRoutes = async () => {
    comparisonController.current?.abort()
    const controller = new AbortController()
    comparisonController.current = controller
    setComparing(true)
    setComparison(null)
    setRouteError('')
    try {
      const query = routeQuery()
      query.set('repetitions', String(repetitions))
      const result = await getJson<ComparisonReport>(`${base}/compare?${query}`, controller.signal)
      if (!controller.signal.aborted) setComparison(result)
    } catch (err) {
      if (!controller.signal.aborted) setRouteError((err as Error).message)
    } finally { if (!controller.signal.aborted) setComparing(false) }
  }
  const onFeature = useCallback((feature: ExternalFeature) => setSelected(feature), [])
  const overlays = snapshot
    ? { ...snapshot, showPopulation, showZones, onFeature, onLocation, grid: grid ?? undefined, showGrid, onCell: setSelectedCell, route, endpoints: endpoints ?? undefined, showReference }
    : undefined
  return (
    <>
      {props.dataset.has_experiment && (
        <section className="external-panel" aria-label="External layers">
          <h3>Independent source layers</h3>
          {error && <p role="alert">External data unavailable: {error}</p>}
          {!snapshot && !error && <p role="status">Verifying saved external payloads…</p>}
          {snapshot && (
            <>
              <p>
                {snapshot.experiment.synthetic
                  ? 'Synthetic test fixture'
                  : 'Saved research experiment'}{' '}
                · {snapshot.experiment.config.scenario} · {snapshot.experiment.config.agl_m} m AGL
              </p>
              <p className="subtle">
                {snapshot.experiment.config.mission_start} –{' '}
                {snapshot.experiment.config.mission_end} ({snapshot.experiment.config.timezone})
              </p>
              <div className="external-controls">
                <label>
                  Grid cell (m)
                  <input type="number" min="1" step="1" value={cellSize}
                    onChange={(e) => setCellSize(Number(e.target.value))} />
                </label>
                <label>
                  <input type="checkbox" checked={showGrid} onChange={(e) => setShowGrid(e.target.checked)} />{' '}
                  Constraint grid
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={showPopulation}
                    onChange={(e) => setShowPopulation(e.target.checked)}
                  />{' '}
                  GHSL population ({snapshot.experiment.config.ghsl_epoch}{' '}
                  {snapshot.experiment.config.ghsl_epoch === 2020 ? 'estimate' : 'projection'})
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={showZones}
                    onChange={(e) => setShowZones(e.target.checked)}
                  />{' '}
                  DIPUL zones
                </label>
                <button onClick={() => setPoint(snapshot.experiment.config.start)}>
                  Inspect start
                </button>
                <button onClick={() => setPoint(snapshot.experiment.config.end)}>
                  Inspect end
                </button>
              </div>
              {gridError && <p role="alert">Grid unavailable: {gridError}</p>}
              {endpoints && <div className="routing-controls" aria-label="Route planning">
                <h3>Route planning</h3>
                <div className="external-controls">
                  <label>Algorithm <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
                    <option value="astar">A*</option><option value="dijkstra">Dijkstra</option><option value="abitstar">ABIT*</option>
                  </select></label>
                  <label>Objective <select value={objective} onChange={(e) => setObjective(e.target.value)}>
                    <option value="distance">Distance</option><option value="risk">Weighted building risk</option>
                  </select></label>
                  <label>Risk weight <input type="number" min="0" step="0.1" value={riskWeight} onChange={(e) => setRiskWeight(Number(e.target.value))} /></label>
                  <label>Distance weight <input type="number" min="0" step="0.1" value={distanceWeight} onChange={(e) => setDistanceWeight(Number(e.target.value))} /></label>
                  <label>Background score assumption <input type="number" min="0" step="any" placeholder="Unassessed" value={backgroundCost} onChange={(e) => setBackgroundCost(e.target.value)} /></label>
                  <label>Safety distance (m) <input type="number" min="0" step="any" value={safetyDistance} onChange={(e) => setSafetyDistance(Number(e.target.value))} /></label>
                  <label>ABIT* budget (s) <input type="number" min="0" max="60" step="0.1" value={budget} onChange={(e) => setBudget(Number(e.target.value))} /></label>
                </div>
                {(['start', 'end'] as const).map((name) => <div key={name} className="external-controls">
                  <button onClick={() => setSelection(name)}>Select {name} on map</button>
                  {([0, 1] as const).map((axis) => <label key={axis}>{name} {axis === 0 ? 'longitude' : 'latitude'}
                    <input type="number" step="any" value={endpoints[name][axis]} onChange={(event) => {
                      const coordinate: [number, number] = [...endpoints[name]]
                      coordinate[axis] = Number(event.target.value)
                      setEndpoints({ ...endpoints, [name]: coordinate })
                    }} />
                  </label>)}
                </div>)}
                {selection !== 'inspect' && <p role="status">Click the map to choose {selection}. <button onClick={() => setSelection('inspect')}>Cancel selection</button></p>}
                <div className="external-controls">
                  <button disabled={!grid || routing || comparing} onClick={generateRoute}>{routing ? 'Searching…' : 'Generate route'}</button>
                  <button disabled={!route || routing} onClick={exportRoute}>Export route GeoJSON</button>
                  <label><input type="checkbox" checked={showReference} onChange={(e) => setShowReference(e.target.checked)} /> Straight-line reference (not constraint validated)</label>
                </div>
                {routeError && <p role="alert">Route unavailable: {routeError}</p>}
                {route && <div role="status" data-testid="route-result">
                  <strong>{routeLabels[route.status] ?? route.status}</strong>{route.message && `: ${route.message}`}
                  {route.length_m != null && <p>Horizontal length: {route.length_m.toFixed(3)} m</p>}
                  <p>Runtime: {route.runtime_ms.toFixed(1)} ms · {route.algorithm} · {route.objective} · {route.rules_version}</p>
                  <p>Solution: {route.solution_kind} · exact: {String(route.exact)}</p>
                  <p>Risk length cost: {number(route.risk_length_cost)} · objective cost: {number(route.objective_cost)}</p>
                  <p>{route.optimality}</p>
                  <details><summary>Model assumptions and controls</summary><pre>{JSON.stringify({ controls: route.controls, assumptions: route.assumptions, risk_model: route.risk_model }, null, 2)}</pre></details>
                  {route.candidate != null && <p>Approximate candidate is diagnostic only; no exact route geometry is exported.</p>}
                  {route.experiment.synthetic && <p>Synthetic constraint demo; no real flight applicability.</p>}
                </div>}
                <p className="subtle">Distance uses length only. Weighted risk integrates building scores along the route; background must be explicitly assessed. Population does not affect this objective. Unknown real restriction coverage prevents a validated route.</p>
                <div className="external-controls">
                  <label>ABIT* repetitions <input type="number" min="1" max="10" value={repetitions} onChange={(e) => setRepetitions(Number(e.target.value))} /></label>
                  <button disabled={!grid || routing || comparing} onClick={compareRoutes}>{comparing ? 'Comparing…' : 'Compare algorithms'}</button>
                  <button disabled={!comparison || comparing} onClick={() => download(comparison, `${props.dataset.id}-comparison.json`, 'application/json')}>Export comparison</button>
                </div>
                <p className="subtle">Comparison uses the selected endpoints, weights, background, clearance and grid. Total ABIT* budgets are limited to 60 s. Per-task random seeding is unavailable.</p>
                {comparison && <div data-testid="comparison-result">
                  <p>{comparison.synthetic ? 'Synthetic experiment' : 'Saved real-data experiment'} · {comparison.status}</p>
                  <div className="table-scroll"><table><thead><tr><th>Planner</th><th>Status</th><th>Length (m)</th><th>Risk cost</th><th>Comparable objective</th><th>Runtime (ms)</th><th>Verification</th></tr></thead>
                    <tbody>{comparison.runs.map((run) => <tr key={run.label}><td>{run.label}</td><td>{run.result.status}</td><td>{number(run.result.length_m)}</td><td>{number(run.comparison_costs.risk_length_cost)}</td><td>{number(run.comparison_costs.objective_cost)}</td><td>{run.result.runtime_ms.toFixed(1)}</td><td>{run.comparison_costs.status}</td></tr>)}</tbody></table></div>
                  <p>Verified ABIT* exact-solution rate: {(comparison.abitstar_summary.verified_exact_solution_rate * 100).toFixed(1)}% / {comparison.abitstar_summary.repetitions} runs</p>
                  {comparison.abitstar_summary.objective_distribution && <p>Objective distribution: {JSON.stringify(comparison.abitstar_summary.objective_distribution)}</p>}
                  {comparison.limitations.map((item) => <p className="subtle" key={item}>{item}</p>)}
                </div>}
              </div>}
              {grid && <p className="subtle">{grid.cell_count} cells · {grid.edge_count} candidate edges · unresolved inputs blocked by policy. Click a grid cell for reasons.</p>}
              <div className="external-legend" aria-label="Population legend">
                {[
                  [0, '0'],
                  [1, '>0–<25'],
                  [25, '25–<100'],
                  [100, '≥100'],
                  [null, 'Unknown / NoData'],
                ].map(([value, text]) => (
                  <span key={String(text)}>
                    <i style={{ background: populationColor(value) }} />
                    {text}
                  </span>
                ))}
                <span>people / native 100 m cell; color bins only</span>
                <span>
                  <i style={{ background: '#8b5bb5' }} />
                  DIPUL: applicability unresolved
                </span>
              </div>
              <p className="subtle">
                Click inside the query boundary to inspect native values and heights. Population
                footprints retain their full native support. DIPUL shows selected static layers
                only; temporary restrictions and mission-time applicability are unverified.
              </p>
            </>
          )}
        </section>
      )}
      <MapCanvas {...props} external={overlays} />
      {snapshot && (
        <section className="external-panel" aria-label="External inspection">
          <h3>Location and source inspection</h3>
          {inspecting && <p role="status">Inspecting location…</p>}
          {pointError && <p role="alert">{pointError}</p>}
          {location && (
            <div className="external-values" data-testid="external-location">
              <p>
                Location: {location.longitude.toFixed(6)}, {location.latitude.toFixed(6)}
              </p>
              <p>
                AGL: <strong>{location.agl_m} m</strong>
              </p>
              <p>
                Terrain elevation:{' '}
                <strong>
                  {number(location.terrain_m)}
                  {location.terrain_m == null ? '' : ' m'}
                </strong>
              </p>
              <p>
                Aircraft altitude:{' '}
                <strong>
                  {number(location.aircraft_altitude_m)}
                  {location.aircraft_altitude_m == null ? '' : ' m'}
                </strong>
              </p>
              <p>
                Height reference: {location.vertical_datum}; native terrain cell, no interpolation
              </p>
              <p>Population: {number(location.people_per_cell)} people / native 100 m cell</p>
              <p>
                Intersecting saved zones: {location.zones.length}. Applicability unresolved; absence
                is not proof of permission.
              </p>
              {location.zones.map((zone) => (
                <button key={`${zone.source_layer}:${zone.id}`} onClick={() => setSelected(zone)}>
                  {zone.source_layer} / {zone.id}
                </button>
              ))}
            </div>
          )}
          {!location && !inspecting && !pointError && (
            <p>Select a map location or inspect a mission endpoint.</p>
          )}
          {selected && (
            <details open>
              <summary>
                Source feature: {selected.source_layer ?? 'GHSL'} / {selected.id}
              </summary>
              <dl className="properties">
                {Object.entries(selected.properties ?? {}).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>
                      {value == null
                        ? 'Unknown / not supplied'
                        : typeof value === 'object'
                          ? JSON.stringify(value)
                          : String(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            </details>
          )}
          {selectedCell && (
            <details open>
              <summary>Grid cell {selectedCell.id}: {selectedCell.state}</summary>
              <p>Terrain: {number(selectedCell.terrain_m)} m; aircraft altitude: {number(selectedCell.aircraft_altitude_m)} m</p>
              <p>Estimated people in cell: {number(selectedCell.population.estimated_people)}; density: {number(selectedCell.population.people_per_km2)} people/km²; unknown support: {selectedCell.population.unknown_area_m2.toFixed(1)} m². Native GHSL support: {selectedCell.population.native_support_m} m.</p>
              {selectedCell.reasons.map((item, index) => <p key={index}>{item.source}: {item.reason}</p>)}
              <details>
                <summary>Adjacent candidate connections</summary>
                {grid?.edges.filter((edge) => edge.from === selectedCell.id || edge.to === selectedCell.id).map((edge) => (
                  <p key={`${edge.from}:${edge.to}`}>{edge.from} → {edge.to}: {edge.length_m.toFixed(1)} m · {edge.state}; {edge.reasons.map((reason) => `${reason.source}: ${reason.reason}`).join(' ')}</p>
                ))}
              </details>
            </details>
          )}
          {grid && <details>
            <summary>Endpoint connectors</summary>
            <p>{route ? 'Latest selected route endpoints.' : 'Prepared mission endpoints; selected endpoints are checked when generating a route.'}</p>
            {(route?.connectors ?? grid.connectors).map((item) => <p key={item.endpoint}>{item.endpoint} → cell {item.cell}: {item.length_m.toFixed(1)} m · {item.state}; {item.reasons.map((reason) => reason.reason).join(' ')}</p>)}
          </details>}
          <details>
            <summary>Source versions, coverage and provenance</summary>
            <p>Snapshot saved: {snapshot.experiment.saved_at_utc}. Checksums verified on read.</p>
            {Object.entries(snapshot.experiment.sources).map(([key, source]) => (
              <div key={key}>
                <h4>
                  {key.toUpperCase()} — {source.product}
                </h4>
                <p>
                  {source.source_id} · {source.attribution} · {source.license}
                </p>
                {source.raster && (
                  <p>
                    Native resolution: {source.raster.resolution.join(' × ')} m; NoData:{' '}
                    {source.raster.effective_nodata}
                    {source.raster.nodata == null
                      ? ' (product specification; TIFF tag absent)'
                      : ''}
                  </p>
                )}
                {source.coverage && <p>{source.coverage}</p>}
                {source.metadata_discrepancy && <p>{source.metadata_discrepancy}</p>}
              </div>
            ))}
            <p>
              OSM downloads contain OSM only. External originals and the experiment manifest remain
              in the local experiment directory.
            </p>
          </details>
        </section>
      )}
    </>
  )
}
