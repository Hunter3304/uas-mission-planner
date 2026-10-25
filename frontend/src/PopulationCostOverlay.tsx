import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import type { FeatureCollection } from 'geojson'
import { getJson } from './api'
import { costColors, unknownCostColor } from './osmStyles'
import { costLabels, numberText } from './sourcePresentation'
import { selectionFeatureId, useMapSelection } from './mapSelection'

interface DensityBin {
  score: number
  lower_people_per_km2: number
  upper_people_per_km2: number
  upper_inclusive: boolean
}
interface PopulationCosts {
  identity: string
  state: string
  epoch: number
  maximum_people_per_km2: number | null
  all_zero: boolean
  known_cells: number
  unknown_cells: number
  bins: DensityBin[]
  display: { complete: boolean; returned_count: number; matched_count: number; bounds: number[] | null }
  layer: FeatureCollection
}

export default function PopulationCostOverlay({ map, datasetId, visible }: {
  map: L.Map; datasetId: string; visible: boolean
}) {
  const [data, setData] = useState<PopulationCosts>()
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [revision, setRevision] = useState(0)
  const cache = useRef(new Map<string, PopulationCosts>())
  const fullLoaded = useRef(false)
  const viewportMode = useRef(false)
  const pending = useRef<AbortController | null>(null)
  const failed = useRef<{ query: string; attempt: number } | null>(null)
  const { select, reconcile } = useMapSelection()
  const context = useMemo(() => data ? Object.fromEntries(Object.entries(data).filter(([key]) => key !== 'layer')) : {}, [data])
  useEffect(() => {
    if (!visible) return
    let timer: ReturnType<typeof setTimeout>
    const changed = () => {
      if (!viewportMode.current || fullLoaded.current) return
      clearTimeout(timer)
      timer = setTimeout(() => {
        const b = map.getBounds()
        const coords = [Math.max(-180, b.getWest()), Math.max(-85, b.getSouth()), Math.min(180, b.getEast()), Math.min(85, b.getNorth())]
        if (coords[0] < coords[2] && coords[1] < coords[3]) setQuery(`?bbox=${coords.map(v => v.toFixed(6)).join(',')}`)
      }, 200)
    }
    map.on('moveend', changed)
    return () => { clearTimeout(timer); map.off('moveend', changed) }
  }, [map, visible])
  useEffect(() => () => { pending.current?.abort(); pending.current = null }, [])
  useEffect(() => {
    if (!visible) return
    const cached = cache.current.get(fullLoaded.current ? '' : query)
    if (cached) { setData(cached); setLoading(false); setError(''); return }
    if (pending.current || failed.current?.query === query && failed.current.attempt === attempt) return
    const active = new AbortController()
    pending.current = active
    setLoading(true)
    setError('')
    setData(undefined)
    getJson<PopulationCosts>(`/api/datasets/${encodeURIComponent(datasetId)}/study/population-costs${query}`, active.signal)
      .then(response => {
        if (active.signal.aborted) return
        if (!response.layer?.features || !response.display || !Array.isArray(response.bins)) throw new Error('Invalid population class response. Retry the layer.')
        cache.current.set(query, response)
        while (cache.current.size > 2) cache.current.delete(cache.current.keys().next().value!)
        fullLoaded.current = query === '' && response.display.complete
        viewportMode.current = !fullLoaded.current
      })
      .catch(failure => {
        if (!active.signal.aborted) { failed.current = { query, attempt }; setError(failure.message) }
      })
      .finally(() => {
        if (!active.signal.aborted) {
          pending.current = null
          setLoading(false)
          setRevision(v => v + 1)
        }
      })
    // Keep preparation alive across visibility changes; viewport requests queue.
    // Only unmount aborts it. Completion resolves the latest view from the cache.
  }, [datasetId, visible, query, attempt, revision])
  useEffect(() => {
    reconcile('population-cost', visible ? data?.layer.features ?? null : null, data?.identity)
    return () => reconcile('population-cost', null, null)
  }, [data, visible, reconcile])
  useEffect(() => {
    if (!visible || !data) return
    const group = L.geoJSON(data.layer, {
      style: feature => {
        const score = feature?.properties?.risk_score
        const known = Number.isInteger(score) && score >= 0 && score <= 4
        return { color: '#48544c', weight: .7, fillOpacity: .65,
          fillColor: known ? costColors[score] : unknownCostColor,
          dashArray: known ? undefined : '3 3' }
      },
      onEachFeature: (feature, layer) => layer.on('click', (event: L.LeafletMouseEvent) =>
        select({ owner: 'population-cost', source: 'GHSL', id: selectionFeatureId(feature),
          version: data.identity, feature, context, anchor: [event.latlng.lat, event.latlng.lng] })),
    }).addTo(map)
    return () => { group.remove() }
  }, [map, data, visible, context, select])
  return <>
    <div className="cost-legend" aria-label="Population risk legend">
      {costColors.map((color, score) => <span key={score}><i style={{ background: color }} />{score} · {costLabels[score]}</span>)}
      <span><i style={{ background: unknownCostColor }} />NoData</span>
    </div>
    <p className="layer-help">250 m population risk classes · green to red, 0–4. Gray means NoData. Class 0 can still contain people. Classes are relative to the complete saved study. Population is inspection only and does not affect route costs.</p>
    {visible && <div data-testid="population-cost-state" aria-live="polite">
      {loading && <p role="status">Preparing 250 m population classes…</p>}
      {error && <p role="alert">{error} <button type="button" onClick={() => setAttempt(v => v + 1)}>Retry population classes</button></p>}
      {data && <>
        <p className="layer-help">Ready · {data.display.returned_count.toLocaleString()} cells · Epoch: {data.epoch} · Native support: 100 m · Aggregated grid: 250 m.</p>
        {data.state === 'unresolved' && <p role="alert">No completely supported cells. Population classes are unavailable.</p>}
        {!data.display.complete && <p role="status">Display limited to {data.display.returned_count.toLocaleString()} of {data.display.matched_count.toLocaleString()} cells. Zoom or move the map to load a smaller view; study-wide thresholds stay fixed.</p>}
        <details><summary>Population class thresholds</summary>
          <p>{data.all_zero ? 'All supported study cells have a known zero estimate; class 0 applies.' : `Maximum study density: ${data.maximum_people_per_km2 == null ? 'unavailable' : numberText(data.maximum_people_per_km2)} people/km².`}</p>
          {!data.all_zero && data.bins.map(bin => <p key={bin.score}>Class {bin.score}: {numberText(bin.lower_people_per_km2)} ≤ density {bin.upper_inclusive ? '≤' : '<'} {numberText(bin.upper_people_per_km2)} people/km²</p>)}
          <p>Complete supported cells: {data.known_cells.toLocaleString()} · Unknown cells: {data.unknown_cells.toLocaleString()}. Estimated people are aggregated by actual intersected area.</p>
        </details>
      </>}
    </div>}
  </>
}
