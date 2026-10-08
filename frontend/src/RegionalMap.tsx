import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import type { FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import { getJson } from './api'
import { populationColor } from './external'

export interface Site { id: string; name: string; longitude: number; latitude: number; address?: string }
export interface Study { config: { locations: Site[]; bounds: { west: number; south: number; east: number; north: number } }; sources: Record<string, { attribution?: string }> }
export interface ConstraintLayers { blocked: FeatureCollection; unknown: FeatureCollection; diagnostics: unknown[]; provenance: unknown; interpretation: string }
const legend = { boundary: 'Boundary — dashed teal', locations: 'Locations — blue; origin green; destination orange', osm: 'OSM — brown source features', zones: 'Original DIPUL — purple, applicability unverified', blocked: 'Effective constraints — red buffered footprints', unknown: 'Unknown areas — amber buffered footprints', population: 'GHSL — people/native 100 m cell; white zero, pink NoData', route: 'Route — green, successful result only' }
export default function RegionalMap({ datasetId, study, startId, endId, geometry, constraints }: { datasetId: string; study: Study | null; startId: string; endId: string; geometry: Geometry | null; constraints: ConstraintLayers | null }) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const [visible, setVisible] = useState({ boundary: true, locations: true, osm: false, zones: false, blocked: true, unknown: false, population: false, route: true })
  const [layers, setLayers] = useState<Partial<Record<'osm' | 'zones' | 'population', FeatureCollection>>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
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
    const collections = { ...layers, blocked: constraints?.blocked, unknown: constraints?.unknown }
    for (const key of ['population', 'osm', 'zones', 'blocked', 'unknown'] as const) {
      const collection = collections[key]
      if (!visible[key] || !collection) continue
      L.geoJSON(collection, { style: feature => ({ color: { population: '#527b66', osm: '#bc784a', zones: '#8b5bb5', blocked: '#b33e39', unknown: '#c87928' }[key], weight: key === 'population' ? 0.4 : 1.5, fillOpacity: key === 'population' ? 0.55 : 0.2, fillColor: key === 'population' ? populationColor(feature?.properties.people_per_cell) : undefined }), onEachFeature: (feature, layer) => {
        const label = document.createElement('span')
        label.textContent = JSON.stringify(feature.properties)
        layer.bindPopup(label)
      } }).addTo(group)
    }
    if (visible.route && geometry) L.geoJSON({ type: 'FeatureCollection', features: [{ type: 'Feature', geometry, properties: {} }] } as FeatureCollection, { style: { color: '#12664f', weight: 5 } }).addTo(group)
    return () => { group.remove() }
  }, [study, startId, endId, geometry, constraints, layers, visible])
  return <>
    <fieldset><legend>Regional map layers</legend>{(Object.keys(legend) as (keyof typeof legend)[]).map(key => <label key={key} style={{ display: 'block' }}><input type="checkbox" checked={visible[key]} onChange={event => setVisible(current => ({ ...current, [key]: event.target.checked }))} /> {legend[key]}{visible[key] && ['osm', 'zones', 'population'].includes(key) && !layers[key as keyof typeof layers] && ' · loading or unavailable'}</label>)}</fieldset>
    <div className="map-shell"><div className="map" style={{ minHeight: 480 }} ref={container} role="region" aria-label="Hannover regional map" /></div>
    <p>Saved source data: {study ? Object.values(study.sources).map(source => source.attribution).filter(Boolean).join(' · ') : 'Loading verified study…'}. GHSL is inspection only.</p>
    {Object.entries(errors).filter(([key, value]) => value && visible[key as keyof typeof visible]).map(([key, value]) => <p key={key} role="alert">{key}: {value}</p>)}
    {!constraints && <p>Effective constraints and unknown areas require an explicit scenario. Load scenario layers in the planning panel.</p>}
    {constraints && <details><summary>Layer coverage and applicability findings</summary><p>{constraints.interpretation}</p><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(constraints.diagnostics, null, 2)}</pre></details>}
  </>
}
