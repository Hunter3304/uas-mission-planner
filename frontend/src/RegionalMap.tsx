import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import type { FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import { getJson } from './api'
import { populationColor } from './external'
import type { RestrictionReport } from './RestrictionProfiles'

export interface Site { id: string; name: string; longitude: number; latitude: number; address?: string }
export interface Study { config: { locations: Site[]; bounds: { west: number; south: number; east: number; north: number } }; sources: Record<string, { attribution?: string }> }
export interface ConstraintLayers { blocked: FeatureCollection; unknown: FeatureCollection; excluded?: FeatureCollection; allowed?: FeatureCollection; inactive?: FeatureCollection; restriction_report?: RestrictionReport; diagnostics: unknown[]; provenance: unknown; interpretation: string }
const legend = { boundary: 'Boundary — dashed teal', locations: 'Locations — blue; origin green; destination orange', osm: 'OSM — brown source features', zones: 'Original DIPUL — purple, applicability unverified', blocked: 'Effective constraints — red buffered footprints', excluded: 'Policy exclusions — orange, unresolved zones', allowed: 'Conditions satisfied — blue, scoped evidence', inactive: 'Not applicable — gray, scenario only', unknown: 'Unknown areas — amber buffered footprints', population: 'GHSL — people/native 100 m cell; white zero, pink NoData', route: 'Route — green, successful result only' }
export default function RegionalMap({ datasetId, study, startId, endId, geometry, constraints }: { datasetId: string; study: Study | null; startId: string; endId: string; geometry: Geometry | null; constraints: ConstraintLayers | null }) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const [visible, setVisible] = useState({ boundary: true, locations: true, osm: false, zones: false, blocked: true, excluded: true, allowed: false, inactive: false, unknown: false, population: false, route: true })
  const [layers, setLayers] = useState<Partial<Record<'osm' | 'zones' | 'population', FeatureCollection>>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [basemap, setBasemap] = useState(true)
  const [tileError, setTileError] = useState(false)
  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, { preferCanvas: true, zoomAnimation: false }).setView([52.38, 9.9], 11)
    map.current = instance
    L.control.scale({ imperial: false }).addTo(instance)
    const observer = new ResizeObserver(() => instance.invalidateSize())
    observer.observe(container.current)
    return () => { observer.disconnect(); instance.remove(); map.current = null }
  }, [])
  useEffect(() => {
    if (!map.current || !basemap) return
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map.current)
    tiles.on('tileerror', () => setTileError(true))
    return () => { tiles.off(); tiles.remove() }
  }, [basemap])
  useEffect(() => {
    if (!study || !map.current) return
    const b = study.config.bounds
    map.current.fitBounds([[b.south, b.west], [b.north, b.east]], { animate: false })
  }, [study])
  useEffect(() => {
    const active = new AbortController()
    for (const key of ['osm', 'zones', 'population'] as const) {
      if (!visible[key] || layers[key]) continue
      const suffix = key === 'osm' ? '/features' : key === 'zones' ? '/study/layers/zones' : '/study/population?cells=true'
      getJson<FeatureCollection | { layer: FeatureCollection }>(`/api/datasets/${encodeURIComponent(datasetId)}${suffix}`, active.signal)
        .then(response => { if (!active.signal.aborted) { setLayers(current => ({ ...current, [key]: 'layer' in response ? response.layer : response })); setErrors(current => ({ ...current, [key]: '' })) } })
        .catch(error => { if (!active.signal.aborted) setErrors(current => ({ ...current, [key]: error.message })) })
    }
    return () => active.abort()
  }, [datasetId, visible, layers])
  useEffect(() => {
    const instance = map.current
    if (!instance) return
    const group = L.layerGroup().addTo(instance)
    if (study && visible.boundary) {
      const b = study.config.bounds
      L.rectangle([[b.south, b.west], [b.north, b.east]], { color: '#183e43', dashArray: '6 6', fill: false }).addTo(group)
    }
    if (study && visible.locations) for (const site of study.config.locations) {
      const color = site.id === startId ? '#12664f' : site.id === endId ? '#c15733' : '#305fbc'
      const label = document.createElement('span')
      label.textContent = `${site.name} (${site.id})${site.id === startId ? ' · Origin' : ''}${site.id === endId ? ' · Destination' : ''}`
      L.circleMarker([site.latitude, site.longitude], { color, radius: 7, fillOpacity: 1 }).bindTooltip(label).addTo(group)
    }
    const collections = { ...layers, blocked: constraints?.blocked, unknown: constraints?.unknown, excluded: constraints?.excluded, allowed: constraints?.allowed, inactive: constraints?.inactive }
    for (const key of ['population', 'osm', 'zones', 'blocked', 'unknown', 'excluded', 'allowed', 'inactive'] as const) {
      const collection = collections[key]
      if (!visible[key] || !collection) continue
      L.geoJSON(collection, { style: feature => ({ color: { population: '#527b66', osm: '#bc784a', zones: '#8b5bb5', blocked: '#b33e39', unknown: '#c87928', excluded: '#df6800', allowed: '#305fbc', inactive: '#777777' }[key], weight: key === 'population' ? 0.4 : 1.5, fillOpacity: key === 'population' ? 0.55 : 0.2, fillColor: key === 'population' ? populationColor(feature?.properties.people_per_cell) : undefined }), onEachFeature: (feature, layer) => {
        const label = document.createElement('span')
        label.textContent = JSON.stringify(feature.properties)
        layer.bindPopup(label)
      } }).addTo(group)
    }
    if (visible.route && geometry) L.geoJSON({ type: 'FeatureCollection', features: [{ type: 'Feature', geometry, properties: {} }] } as FeatureCollection, { style: { color: '#12664f', weight: 5 } }).addTo(group)
    return () => { group.remove() }
  }, [study, startId, endId, geometry, constraints, layers, visible])
  return <>
    <label><input type="checkbox" checked={basemap} onChange={event => { setBasemap(event.target.checked); setTileError(false) }} /> Street basemap — online OpenStreetMap tiles</label>
    {basemap && tileError && <p role="alert">Street basemap tiles could not load. Check your internet connection; saved locations and data layers remain available.</p>}
    <fieldset><legend>Regional map layers</legend>{(Object.keys(legend) as (keyof typeof legend)[]).map(key => <label key={key} style={{ display: 'block' }}><input type="checkbox" checked={visible[key]} onChange={event => setVisible(current => ({ ...current, [key]: event.target.checked }))} /> {legend[key]}{visible[key] && ['osm', 'zones', 'population'].includes(key) && !layers[key as keyof typeof layers] && ' · loading or unavailable'}</label>)}</fieldset>
    <div className="map-shell"><div className="map" style={{ minHeight: 480 }} ref={container} role="region" aria-label="Hannover regional map" /></div>
    <p>Saved source data: {study ? Object.values(study.sources).map(source => source.attribution).filter(Boolean).join(' · ') : 'Loading verified study…'}. GHSL is inspection only.</p>
    {Object.entries(errors).filter(([key, value]) => value && visible[key as keyof typeof visible]).map(([key, value]) => <p key={key} role="alert">{key}: {value}</p>)}
    {!constraints && <p>Effective constraints and unknown areas require an explicit scenario. Load scenario layers in the planning panel.</p>}
    {constraints?.restriction_report && <p>Zone decisions: {Object.entries(constraints.restriction_report.counts).map(([key, value]) => `${key}: ${value}`).join(' · ')} · Policy exclusions: {constraints.restriction_report.policy_exclusions ?? 0}. Coverage: {constraints.restriction_report.coverage.status}.</p>}
    {constraints?.restriction_report?.building_counts && <p>Original building records (separate from zones): {Object.entries(constraints.restriction_report.building_counts).map(([key, value]) => `${key}: ${value}`).join(' · ')}. Height estimates and derived geometry remain scenario assumptions.</p>}
    {constraints && <details><summary>Layer coverage and applicability findings</summary><p>{constraints.interpretation}</p><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(constraints.diagnostics, null, 2)}</pre></details>}
  </>
}
