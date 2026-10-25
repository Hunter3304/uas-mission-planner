import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import PopulationCostOverlay from './PopulationCostOverlay'
import type { RestrictionReport } from './RestrictionProfiles'
import RegionalOsm from './RegionalOsm'
import CollapsiblePanel from './CollapsiblePanel'
import { decisionKeys, groupScenarioLayers, type DecisionKey, type LayerSource, type ScenarioLayerKey } from './regionalLayers'
import { MapSelectionProvider, SelectionOverlay } from './RegionalSelection'
import { selectionFeatureId, useMapSelection, type MapSelection } from './mapSelection'
import { asRecord } from './sourcePresentation'

export interface Site {
  id: string
  name: string
  longitude: number
  latitude: number
  address?: string
}
export interface Study {
  config: {
    locations: Site[]
    bounds: { west: number; south: number; east: number; north: number }
  }
  sources: Record<string, { attribution?: string }>
}
export interface ConstraintLayers {
  flight_interval?: { mode: 'provisional'; assessed_interval: { mission_start: string; mission_end: string }; interpretation: string }
  blocked: FeatureCollection
  unknown: FeatureCollection
  excluded?: FeatureCollection
  allowed?: FeatureCollection
  inactive?: FeatureCollection
  restriction_report?: RestrictionReport
  diagnostics: unknown[]
  provenance: unknown
  interpretation: string
}
const legend = {
  boundary: 'Boundary — dashed teal',
  locations: 'Locations — blue; origin green; destination orange',
  route: 'Route — green, successful result only',
}
const decisionLabels: Record<DecisionKey, string> = {
  blocked: 'Effective constraints — red buffered footprints',
  excluded: 'Policy exclusions — orange, unresolved zones',
  allowed: 'Conditions satisfied — blue, scoped evidence',
  inactive: 'Not applicable — gray, scenario only',
  unknown: 'Unknown areas — amber buffered footprints',
}
const decisionColors: Record<DecisionKey, string> = { blocked: '#b33e39', excluded: '#df6800', allowed: '#305fbc', inactive: '#777777', unknown: '#c87928' }
export interface ScenarioLayerState { pendingReason: string; loading: boolean; error: string; retry: () => void }
export default function RegionalMap(props: Parameters<typeof RegionalMapContent>[0]) {
  return <MapSelectionProvider><RegionalMapContent {...props} /></MapSelectionProvider>
}
function RegionalMapContent({
  datasetId,
  study,
  startId,
  endId,
  startCoordinate,
  endCoordinate,
  exactCoordinates,
  geometry,
  constraints,
  layerVisibility,
  onLayerVisibility,
  layerState,
}: {
  datasetId: string
  study: Study | null
  startId: string
  endId: string
  startCoordinate?: [number, number]
  endCoordinate?: [number, number]
  exactCoordinates: boolean
  geometry: Geometry | null
  constraints: ConstraintLayers | null
  layerVisibility: Record<ScenarioLayerKey, boolean>
  onLayerVisibility: (next: Record<ScenarioLayerKey, boolean>) => void
  layerState: ScenarioLayerState
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const [readyMap, setReadyMap] = useState<L.Map | null>(null)
  const scenarioContext = useMemo(() => {
    const p = asRecord(constraints?.provenance)
    return Object.fromEntries(['scenario', 'restriction_coverage', 'model_signature', 'restrictions_rules_version', 'study_signature'].filter(key => p[key] != null).map(key => [key, p[key]]))
  }, [constraints])
  const [visible, setVisible] = useState({
    boundary: true,
    locations: true,
    population: false,
    route: true,
  })
  const [basemap, setBasemap] = useState(true)
  const [tileError, setTileError] = useState(false)
  const grouped = useMemo(() => groupScenarioLayers(constraints), [constraints])
  const [startLon, startLat] = startCoordinate ?? []
  const [endLon, endLat] = endCoordinate ?? []
  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, { preferCanvas: true, zoomAnimation: false, fadeAnimation: false }).setView(
      [52.38, 9.9],
      11,
    )
    map.current = instance
    instance.createPane('regional-route').style.zIndex = '450'
    setReadyMap(instance)
    L.control.scale({ imperial: false }).addTo(instance)
    const observer = new ResizeObserver(() => instance.invalidateSize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      instance.remove()
      map.current = null
    }
  }, [])
  useEffect(() => {
    if (!map.current || !basemap) return
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map.current)
    const onTileError = () => setTileError(true)
    tiles.on('tileerror', onTileError)
    // Keep Leaflet's own remove listeners so its map event handlers are released.
    return () => {
      tiles.off('tileerror', onTileError)
      tiles.remove()
    }
  }, [basemap])
  useEffect(() => {
    if (!study || !map.current) return
    const b = study.config.bounds
    map.current.fitBounds(
      [
        [b.south, b.west],
        [b.north, b.east],
      ],
      { animate: false },
    )
  }, [study])
  useEffect(() => {
    const instance = map.current
    if (!instance) return
    const group = L.layerGroup().addTo(instance)
    if (study && visible.boundary) {
      const b = study.config.bounds
      L.rectangle(
        [
          [b.south, b.west],
          [b.north, b.east],
        ],
        { color: '#183e43', dashArray: '6 6', fill: false, interactive: false },
      ).addTo(group)
    }
    if (study && visible.locations)
      for (const site of study.config.locations) {
        const color = !exactCoordinates && site.id === startId ? '#12664f' : !exactCoordinates && site.id === endId ? '#c15733' : '#305fbc'
        const label = document.createElement('span')
        label.textContent = `${site.name} (${site.id})${!exactCoordinates && site.id === startId ? ' · Origin' : ''}${!exactCoordinates && site.id === endId ? ' · Destination' : ''}`
        L.circleMarker([site.latitude, site.longitude], { color, radius: 7, fillOpacity: 1 })
          .bindTooltip(label)
          .addTo(group)
      }
    if (visible.locations && exactCoordinates)
      for (const [name, coordinates, color] of [['Origin', startLon == null || startLat == null ? null : [startLon, startLat], '#12664f'], ['Destination', endLon == null || endLat == null ? null : [endLon, endLat], '#c15733']] as const) {
        if (!coordinates) continue
        const label = document.createElement('span')
        label.textContent = `${name} · Exact coordinates (${coordinates[0]}, ${coordinates[1]})`
        L.circleMarker([coordinates[1], coordinates[0]], { color, radius: 8, fillOpacity: 1 }).bindTooltip(label).addTo(group)
      }
    return () => {
      group.remove()
    }
  }, [study, startId, endId, exactCoordinates, startLon, startLat, endLon, endLat, visible.boundary, visible.locations])
  useEffect(() => {
    if (!readyMap || !visible.route || !geometry) return
    // Noninteractive SVG above the shared canvas cannot intercept OSM clicks.
    const renderer = L.svg({ pane: 'regional-route' })
    const route = L.geoJSON({ type: 'Feature', geometry, properties: {} } as Feature, {
      interactive: false,
      style: { renderer, color: '#12664f', weight: 5 },
    }).addTo(readyMap)
    return () => {
      route.remove()
      renderer.remove()
    }
  }, [readyMap, visible.route, geometry])
  function scenarioControls(source: LayerSource, decisions: readonly DecisionKey[]) {
    const enabled = decisions.some(key => layerVisibility[`${source}:${key}`])
    const count = decisions.reduce((total, key) => total + grouped[`${source}:${key}`].features.length, 0)
    return <div className="scenario-source-controls">
      {decisions.map(key => {
        const id: ScenarioLayerKey = `${source}:${key}`
        const label = source === 'osm' ? (key === 'blocked' ? 'Building obstacles — red buffered footprints' : 'Uncertain building areas — amber') : decisionLabels[key]
        return <label className="map-layer-choice" key={id}><input type="checkbox" checked={layerVisibility[id]} onChange={event => onLayerVisibility({ ...layerVisibility, [id]: event.target.checked })} />{label}</label>
      })}
      {enabled && <div className="layer-load-state" data-testid={`${source}-layer-state`} role={layerState.error ? 'alert' : 'status'}>
        {layerState.pendingReason ? `Pending inputs: ${layerState.pendingReason}` : layerState.loading ? 'Loading scenario layers…' : layerState.error ? <>{layerState.error} <button type="button" onClick={layerState.retry}>Retry {source.toUpperCase()} scenario layers</button></> : constraints ? (count ? `Ready · ${count.toLocaleString()} features in this group. Loaded data are reused when toggling layers.` : 'Ready · No matching features for this scenario.') : 'Scenario layers are hidden.'}
      </div>}
    </div>
  }
  return (
    <>
      <section className="regional-map-controls" aria-label="Map layers">
        <div className="map-controls-heading"><h3>Map layers</h3><span>Expand a source to manage its display</span></div>
        <div className="map-controls-grid">
          <CollapsiblePanel className="map-layer-group" title="Base map & references">
            <label className="map-layer-choice"><input type="checkbox" checked={basemap} onChange={event => { setBasemap(event.target.checked); setTileError(false) }} />Street basemap — online OpenStreetMap tiles</label>
            {basemap && tileError && <p role="alert">Street basemap tiles could not load. Check your internet connection; saved locations and data layers remain available.</p>}
            {(Object.keys(legend) as (keyof typeof legend)[]).map(key => <label className="map-layer-choice" key={key}><input type="checkbox" checked={visible[key]} onChange={event => setVisible(current => ({ ...current, [key]: event.target.checked }))} />{legend[key]}</label>)}
            <div className="osm-selectors">
              {[{ coordinates: startCoordinate, label: 'Focus origin' }, { coordinates: endCoordinate, label: 'Focus destination' }].map(({ coordinates, label }) => <button type="button" key={label} disabled={!coordinates} onClick={() => { if (coordinates) map.current?.setView([coordinates[1], coordinates[0]], 16, { animate: false }) }}>{label}</button>)}
              <button type="button" disabled={!study} onClick={() => { if (study) { const b = study.config.bounds; map.current?.fitBounds([[b.south, b.west], [b.north, b.east]], { animate: false }) } }}>Fit study</button>
            </div>
            <p className="layer-help">Street tiles are online background imagery. Saved source layers work independently. Fit study changes the map extent only.</p>
          </CollapsiblePanel>
          <CollapsiblePanel className="map-layer-group" title="GHSL population">
            <label className="map-layer-choice"><input type="checkbox" checked={visible.population} onChange={event => setVisible(current => ({ ...current, population: event.target.checked }))} />GHSL — population risk (250 m)</label>
            {readyMap && <PopulationCostOverlay key={`${datasetId}:population-cost`} map={readyMap} datasetId={datasetId} visible={visible.population} />}
          </CollapsiblePanel>
          <CollapsiblePanel className="map-layer-group map-layer-group-osm" title="OSM">
            {readyMap && <RegionalOsm key={datasetId} map={readyMap} datasetId={datasetId} />}
            {scenarioControls('osm', ['blocked', 'unknown'])}
          </CollapsiblePanel>
          <CollapsiblePanel className="map-layer-group" title="DIPUL restrictions">
            {scenarioControls('dipul', decisionKeys)}
            <p className="layer-help">Scenario decisions: confirmed prohibitions and unresolved policy exclusions remain separate.</p>
            {constraints?.restriction_report && <details><summary>Restriction assessment summary</summary><p>{Object.entries(constraints.restriction_report.counts).map(([key, value]) => `${key}: ${value}`).join(' · ')}. Coverage: {constraints.restriction_report.coverage.status}.</p></details>}
          </CollapsiblePanel>
          <CollapsiblePanel className="map-layer-group" title="Scenario coverage & diagnostics">
            <p className="layer-help">Regional uncertainty, reviewed notices and findings without a DIPUL or building source.</p>
            {scenarioControls('coverage', decisionKeys)}
            {constraints && <details><summary>Layer coverage and applicability findings</summary><p>{constraints.interpretation}</p><pre>{JSON.stringify(constraints.diagnostics, null, 2)}</pre></details>}
          </CollapsiblePanel>
        </div>
      </section>
      {readyMap && (Object.keys(grouped) as ScenarioLayerKey[]).map(key => <GeoOverlay key={key} owner={`scenario:${key}`} source={key.startsWith('dipul:') ? 'DIPUL' : key.startsWith('osm:') ? 'OSM' : 'Scenario'} context={scenarioContext} map={readyMap} collection={grouped[key]} visible={layerVisibility[key]} color={decisionColors[key.split(':')[1] as DecisionKey]} />)}
      <div className="map-shell"><div className="map" style={{ minHeight: 480 }} ref={container} role="region" aria-label="Hannover regional map" /></div>
      {readyMap && <SelectionOverlay map={readyMap} />}
      <details className="regional-source-attribution"><summary>Saved source attribution</summary><p>{study ? Object.values(study.sources).map(source => source.attribution).filter(Boolean).join(' · ') : 'Loading study catalog…'}</p></details>
    </>
  )
}

function GeoOverlay({
  map,
  collection,
  visible,
  color,
  owner,
  source,
  context,
}: {
  map: L.Map
  collection?: FeatureCollection
  visible: boolean
  color: string
  owner: string
  source: MapSelection['source']
  context?: Record<string, unknown>
}) {
  const { select, reconcile } = useMapSelection()
  useEffect(() => {
    reconcile(owner, visible ? collection?.features ?? null : null, collection)
    return () => { reconcile(owner, null, null) }
  }, [owner, collection, visible, reconcile])
  useEffect(() => {
    if (!visible || !collection) return
    const group = L.geoJSON(collection, {
      style: () => ({
        color,
        weight: 1.5,
        fillOpacity: 0.2,
      }),
      onEachFeature: (feature, layer) =>
        layer.on('click', (event: L.LeafletMouseEvent) => {
          select({ owner, source, id: selectionFeatureId(feature), version: collection, feature, context, anchor: [event.latlng.lat, event.latlng.lng] })
        }),
    }).addTo(map)
    return () => {
      group.remove()
    }
  }, [map, collection, visible, color, owner, source, context, select])
  return null
}
