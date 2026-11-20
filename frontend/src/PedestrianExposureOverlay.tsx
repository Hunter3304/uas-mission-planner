
import { useEffect, useState } from 'react'
import L from 'leaflet'
import type { FeatureCollection } from 'geojson'
import { getJson } from './api'
import { selectionFeatureId, useMapSelection } from './mapSelection'
import { numberText } from './sourcePresentation'
import { pedestrianWindows, type PedestrianWindow, type PedestrianWindowId } from './pedestrianTime'

interface PedestrianLayer {
  state: 'ready' | 'unavailable'
  window: PedestrianWindow
  layer: FeatureCollection
  input_kind?: 'mid-public'
  display_max_people?: number
  model_version?: string
  identity?: string
  reason?: string
}

const colors = ['#f8f5fb', '#dfcce9', '#bc90cb', '#8d57a7', '#582d73']
const thresholds = [.05, .2, .5, 1]
const unavailable = '#9297a0'
const owner = 'pedestrian-exposure'

export default function PedestrianExposureOverlay({ map, datasetId, departureWindow, routeLayerIdentity }: {
  map: L.Map; datasetId: string; departureWindow?: PedestrianWindowId | null; routeLayerIdentity?: string
}) {
  const followsDeparture = departureWindow !== undefined
  const [manualEnabled, setManualEnabled] = useState(false)
  const [showDeparture, setShowDeparture] = useState(true)
  const [manualWindow, setManualWindow] = useState<PedestrianWindowId>('08-10')
  const enabled = followsDeparture ? showDeparture : manualEnabled
  const scenario = followsDeparture ? departureWindow : manualWindow
  const [revision, setRevision] = useState(0)
  const [request, setRequest] = useState<{ key: string; data?: PedestrianLayer; error?: string }>()
  const requestKey = [datasetId, scenario, revision, routeLayerIdentity].join(':')
  const current = request?.key === requestKey ? request : undefined
  const changed = current?.data?.state === 'ready' && routeLayerIdentity !== undefined && current.data.identity !== routeLayerIdentity
  const data = enabled && !changed ? current?.data : undefined
  const maximum = data?.display_max_people ?? 0
  const { select, reconcile } = useMapSelection()

  useEffect(() => {
    if (!enabled || !scenario) return
    const active = new AbortController()
    const endpoint = '/api/datasets/' + encodeURIComponent(datasetId) + '/study/pedestrian-exposure?scenario=' + scenario
    getJson<PedestrianLayer>(endpoint, active.signal)
      .then(response => {
        if (active.signal.aborted) return
        if (response.window?.id !== scenario || !Array.isArray(response.layer?.features) ||
            (response.state !== 'ready' && response.state !== 'unavailable')) {
          throw new Error('The pedestrian layer response is invalid.')
        }
        setRequest({ key: requestKey, data: response })
      })
      .catch(error => {
        if (!active.signal.aborted) setRequest({ key: requestKey, error: error.message })
      })
    return () => active.abort()
  }, [datasetId, enabled, requestKey, scenario])

  useEffect(() => {
    reconcile(owner, data?.layer.features ?? null, data?.identity)
    return () => reconcile(owner, null, null)
  }, [data, reconcile])

  useEffect(() => {
    if (data?.state !== 'ready') return
    const paneName = 'regional-pedestrian'
    const pane = map.getPane(paneName) ?? map.createPane(paneName)
    pane.style.zIndex = '415'
    const renderer = L.canvas({ pane: paneName })
    const context = {
      window: data.window.label,
      timezone: data.window.timezone,
      model_version: data.model_version,
    }
    const group = L.geoJSON(data.layer, {
      pane: paneName,
      style: feature => {
        const value = feature?.properties?.mean_people
        const band = typeof value === 'number' && value > 0 && maximum > 0
          ? 1 + Math.min(3, thresholds.filter(limit => value > limit * maximum).length)
          : 0
        return { renderer, stroke: false, fillColor: typeof value === 'number' ? colors[band] : unavailable, fillOpacity: .72 }
      },
      onEachFeature: (feature, layer) => layer.on('click', (event: L.LeafletMouseEvent) => {
        select({
          owner,
          source: 'Pedestrian',
          id: selectionFeatureId(feature),
          version: data.identity,
          feature,
          context,
          anchor: [event.latlng.lat, event.latlng.lng],
        })
      }),
    }).addTo(map)
    return () => {
      group.remove()
      renderer.remove()
    }
  }, [data, map, maximum, select])

  return <>
    <label className="map-layer-choice"><input type="checkbox" checked={enabled} onChange={event => (followsDeparture ? setShowDeparture : setManualEnabled)(event.target.checked)} />Show outdoor pedestrian estimates</label>
    {enabled && <>
      {followsDeparture ? <p className="layer-help">{scenario ? `Departure window ${pedestrianWindows.find(([key]) => key === scenario)?.[1]}` : 'Enter a valid departure time to show its exposure window.'}</p> : <div className="osm-selectors">
        <label>Pedestrian time window <select value={manualWindow} onChange={event => setManualWindow(event.target.value as PedestrianWindowId)}>
          {pedestrianWindows.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
      </div>}
      {scenario && (!current || current.error || data?.state === 'unavailable' || changed) && <div className="layer-load-state" role={current?.error || changed ? 'alert' : 'status'}>
        {changed ? 'The saved exposure layer changed. Plan again to compare the route with the current layer.' : !current ? 'Loading pedestrian estimates…' : current.error ?? data?.reason}
        {current && <button type="button" onClick={() => setRevision(n => n + 1)}>Refresh pedestrian estimates</button>}
      </div>}
      {data?.state === 'ready' && <>
        <div className="cost-legend" aria-label="Outdoor pedestrian legend">
          <strong>Mean pedestrians per 150 m cell</strong>
          <span><i style={{ background: colors[0] }} />0</span>
          {maximum > 0 && thresholds.map((limit, index) =>
            <span key={limit}><i style={{ background: colors[index + 1] }} />Up to {numberText(limit * maximum)}</span>,
          )}
          <span><i style={{ background: unavailable }} />Unavailable</span>
        </div>
      </>}
      <p className="layer-help">Resident walking estimate · MiD 2023 municipal estimates and Niedersachsen profiles · all survey days pooled. Times use Europe/Berlin. All windows share one colour scale.</p>
    </>}
  </>
}
