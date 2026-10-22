import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { getJson } from './api'
import { CostDetails, showValue } from './BuildingCosts'
import { categoryColor, costColors, osmStyle, unknownCostColor } from './osmStyles'
import {
  layers,
  type LayerKey,
  type Visibility,
  type OsmIdentity,
  type OsmSummary,
  type OsmCollection,
  type OsmObjectDetail,
} from './types'

const allCategories: Visibility = { building: true, highway: true, landuse: true, natural: true }
const identityKey = (identity: OsmIdentity) =>
  JSON.stringify(Object.entries(identity).sort(([a], [b]) => a.localeCompare(b)))
const objectKey = (feature: OsmCollection['features'][number]) =>
  `${feature.properties.element_type}/${feature.properties.osm_id}`
const MAX_CACHE_BYTES = 8 * 1024 * 1024
interface View {
  data: OsmCollection
  snapshot: string
  notice?: string
}
interface Selection {
  key: string
  snapshot: string
}

function checkCollection(data: OsmCollection, snapshot: string) {
  if (!data.display || identityKey(data.display.identity) !== snapshot)
    throw new Error('The saved OSM snapshot changed. Retry to load its current version.')
  if (
    !Array.isArray(data.features) ||
    data.display.returned_count !== data.features.length ||
    !['detail', 'aggregate_overview'].includes(data.display.representation) ||
    typeof data.display.complete !== 'boolean' ||
    typeof data.display.outside_coverage !== 'boolean' ||
    data.features.length > (data.display.representation === 'aggregate_overview' ? 2000 : 5000) ||
    (data.display.representation === 'detail' &&
      data.features.some((feature) => !Array.isArray(feature.properties?.categories)))
  )
    throw new Error('The OSM response is invalid or exceeds the display limit.')
  return data
}

export default function RegionalOsm({ map, datasetId }: { map: L.Map; datasetId: string }) {
  const [enabled, setEnabled] = useState(true)
  const [visibility, setVisibility] = useState<Visibility>(allCategories)
  const [costMode, setCostMode] = useState(false)
  const [costCategory, setCostCategory] = useState<LayerKey>('building')
  const [summary, setSummary] = useState<OsmSummary | null>(null)
  const [view, setView] = useState<View | null>(null)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [status, setStatus] = useState('Loading saved OSM…')
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const cache = useRef(new Map<string, { data: OsmCollection; bytes: number; notice?: string }>())
  const cacheIdentity = useRef('')
  const base = `/api/datasets/${encodeURIComponent(datasetId)}/study/osm`
  const categories = layers
    .filter(({ key }) => visibility[key])
    .map(({ key }) => key)
    .join(',')

  useEffect(() => {
    let generation = 0
    let active: AbortController | null = null
    let timer: ReturnType<typeof setTimeout> | undefined
    function cancel() {
      generation++
      active?.abort()
      clearTimeout(timer)
      setSelection(null)
      setView(null)
    }
    function moving() {
      cancel()
      setError('')
      if (enabled && categories)
        setStatus(
          'Moving map — waiting for a settled view. Selection clears when the view changes.',
        )
    }
    async function load(ticket: number) {
      active = new AbortController()
      const signal = active.signal
      const current = () => ticket === generation && !signal.aborted
      try {
        // A bounded browser cache never substitutes for checking source readiness.
        const info = await getJson<OsmSummary>(`${base}/summary`, signal)
        if (!current()) return
        if (info.state !== 'ready' || !info.verified) {
          cache.current.clear()
          throw new Error(
            `OSM ${info.state}: ${info.message ?? 'Display data must be prepared and verified before viewing.'}`,
          )
        }
        if (
          !info.identity ||
          !Array.isArray(info.coverage_bounds) ||
          info.coverage_bounds.length !== 4 ||
          !Number.isInteger(info.feature_count) ||
          !Number.isInteger(info.drawable_count) ||
          !info.layer_counts ||
          layers.some(({ key }) => !Number.isInteger(info.layer_counts[key])) ||
          !info.diagnostics?.counts ||
          !Array.isArray(info.diagnostics.samples)
        )
          throw new Error('The OSM summary is invalid. Restart the data service and retry.')
        setSummary(info)
        const snapshot = identityKey(info.identity)
        if (cacheIdentity.current !== snapshot) {
          cache.current.clear()
          cacheIdentity.current = snapshot
        }
        const bounds = map.getBounds().pad(0.1)
        const [west, south, east, north] = info.coverage_bounds
        const bbox = [
          Math.max(west, bounds.getWest()),
          Math.max(south, bounds.getSouth()),
          Math.min(east, bounds.getEast()),
          Math.min(north, bounds.getNorth()),
        ]
        if (bbox[0] >= bbox[2] || bbox[1] >= bbox[3]) {
          setStatus('Outside saved OSM coverage. Moving the map does not acquire new data.')
          return
        }
        const zoom = Math.max(0, Math.min(22, Math.round(map.getZoom())))
        const params = new URLSearchParams({ bbox: bbox.join(','), categories })
        const overview = zoom < 15
        if (!overview) {
          params.set('zoom', String(zoom))
          params.set('style', costMode ? 'cost' : 'category')
          if (costMode) params.set('cost_category', costCategory)
        }
        const url = `${base}/${overview ? 'overview' : 'features'}?${params}`
        const key = `${snapshot}:${url}`
        let entry = cache.current.get(key)
        if (!entry) {
          let data = checkCollection(await getJson<OsmCollection>(url, signal), snapshot)
          if (!current()) return
          let notice: string | undefined
          if (!data.display.complete) {
            notice = `Individual-object display exceeded its limit (${data.display.limit_reason ?? 'bounded response'}).`
            // Discard partial detail; a grid never pretends to be individual objects.
            data = checkCollection(
              await getJson<OsmCollection>(
                `${base}/overview?${new URLSearchParams({ bbox: bbox.join(','), categories })}`,
                signal,
              ),
              snapshot,
            )
            if (!current()) return
          }
          const bytes = new TextEncoder().encode(JSON.stringify(data)).byteLength
          entry = { data, bytes, notice }
          if (bytes <= MAX_CACHE_BYTES) {
            cache.current.set(key, entry)
            while (
              cache.current.size > 4 ||
              [...cache.current.values()].reduce((total, item) => total + item.bytes, 0) >
                MAX_CACHE_BYTES
            )
              cache.current.delete(cache.current.keys().next().value!)
          }
        } else {
          cache.current.delete(key)
          cache.current.set(key, entry)
        }
        if (!current()) return
        setView({ data: entry.data, snapshot, notice: entry.notice })
        setStatus(
          entry.data.display.outside_coverage
            ? 'Outside saved OSM coverage.'
            : entry.data.display.representation === 'aggregate_overview'
              ? 'Aggregate OSM overview — zoom in for individual objects and costs.'
              : entry.data.features.length
                ? `${entry.data.features.length.toLocaleString()} individual OSM objects in the buffered viewport.`
                : 'No matching OSM objects in this viewport.',
        )
      } catch (failure) {
        if (current()) {
          cache.current.clear()
          setView(null)
          setStatus('OSM display unavailable.')
          setError(failure instanceof Error ? failure.message : 'Cannot load saved OSM.')
        }
      }
    }
    function schedule() {
      cancel()
      setError('')
      setSummary(null)
      if (!enabled) {
        setStatus('OSM display is off.')
        return
      }
      if (!categories) {
        setStatus('All OSM categories are hidden.')
        return
      }
      if (costMode && !visibility[costCategory]) {
        setStatus('Enable the selected cost category to display its objects.')
        return
      }
      setStatus('Loading saved OSM…')
      const ticket = generation
      timer = setTimeout(() => {
        void load(ticket)
      }, 180)
    }
    map.on('movestart zoomstart', moving)
    map.on('moveend zoomend', schedule)
    schedule()
    return () => {
      generation++
      active?.abort()
      clearTimeout(timer)
      map.off('movestart zoomstart', moving)
      map.off('moveend zoomend', schedule)
    }
  }, [map, base, enabled, categories, costMode, costCategory, visibility, retry])

  useEffect(() => {
    if (!view || !enabled) return
    const overview = view.data.display.representation === 'aggregate_overview'
    const group = L.geoJSON(view.data, {
      style: (feature) => {
        if (overview) {
          const counts = feature?.properties.category_counts ?? {}
          const dominant = layers
            .filter(({ key }) => visibility[key] && counts[key] > 0)
            .sort((a, b) => counts[b.key] - counts[a.key])[0]
          const color = dominant ? categoryColor([dominant.key], visibility) : '#78838e'
          return { color, fillColor: color, weight: 0.5, fillOpacity: 0.35 }
        }
        const item = feature as OsmCollection['features'][number]
        return osmStyle(item.properties.categories, visibility, costMode, item.cost_analysis)
      },
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          ...osmStyle(
            feature.properties.categories,
            visibility,
            costMode,
            (feature as OsmCollection['features'][number]).cost_analysis,
          ),
          radius: 4,
        }),
      onEachFeature: (feature, layer) => {
        layer.on('click', () => {
          if (overview) {
            const element = document.createElement('span')
            element.textContent = `Aggregate cell: ${feature.properties.objects} unique assigned objects; categories overlap. ${JSON.stringify(feature.properties.category_counts)}. Zoom in for details; this grid shows no cost score.`
            layer.bindPopup(element).openPopup()
          } else
            setSelection({
              key: objectKey(feature as OsmCollection['features'][number]),
              snapshot: view.snapshot,
            })
        })
      },
    })
      .addTo(map)
      .bringToBack()
    return () => {
      group.clearLayers()
      group.remove()
    }
  }, [map, view, enabled, visibility, costMode])

  return (
    <section className="regional-osm" aria-label="Regional OSM display">
      <fieldset>
        <legend>Saved OSM objects</legend>
        <label>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />{' '}
          Show saved OSM
        </label>
        <div className="osm-categories">
          {layers.map((layer) => (
            <label key={layer.key}>
              <input
                type="checkbox"
                checked={visibility[layer.key]}
                onChange={(event) =>
                  setVisibility((current) => ({ ...current, [layer.key]: event.target.checked }))
                }
              />{' '}
              {layer.label}
            </label>
          ))}
        </div>
        <div className="osm-selectors">
          <label>
            OSM color view{' '}
            <select
              value={costMode ? 'cost' : 'category'}
              onChange={(event) => setCostMode(event.target.value === 'cost')}
            >
              <option value="category">Category</option>
              <option value="cost">Independent category cost</option>
            </select>
          </label>
          {costMode && (
            <label>
              OSM cost category{' '}
              <select
                value={costCategory}
                onChange={(event) => {
                  const category = event.target.value as LayerKey
                  setCostCategory(category)
                  setVisibility((current) => ({ ...current, [category]: true }))
                }}
              >
                {layers.map((layer) => (
                  <option key={layer.key} value={layer.key}>
                    {layer.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            type="button"
            onClick={() => {
              cache.current.clear()
              setRetry((value) => value + 1)
            }}
          >
            Refresh OSM
          </button>
        </div>
        <div className="cost-legend" aria-label="OSM legend">
          {costMode && view?.data.display.representation !== 'aggregate_overview' ? (
            <>
              {costColors.map((color, index) => (
                <span key={color}>
                  <i style={{ background: color }} />
                  Cost {index}
                </span>
              ))}
              <span>
                <i style={{ background: unknownCostColor }} />
                Unknown / default / unscored (gray dashed)
              </span>
              <span>Dark outline: historical paper obstruction flag</span>
            </>
          ) : (
            layers.map((layer) => (
              <span key={layer.key}>
                <i style={{ background: layer.color }} />
                {layer.label}
              </span>
            ))
          )}
        </div>
        <p>
          Category precedence: buildings, roads, land use, natural features among enabled
          categories. Costs are independent; blank areas are unassessed.
        </p>
        <p
          role="status"
          data-testid="osm-status"
          data-representation={view?.data.display.representation ?? 'none'}
        >
          {status}
        </p>
        {error && <p role="alert">{error} Use Refresh OSM to retry.</p>}
        {view?.notice && <p>{view.notice} Showing an aggregate overview instead.</p>}
        <details>
          <summary>OSM coverage and counts</summary>
        {view?.data.display.representation === 'aggregate_overview' && (
          <p>
            {view.data.features.length} aggregate cells; color shows the dominant enabled category,
            never a cost score. Counts describe whole cells intersecting the view and use one
            representative point per object; they are not exact viewport totals. Category counts
            overlap.
          </p>
        )}
        {summary?.verified && (
          <p>
            Verified saved study: {summary.feature_count.toLocaleString()} original objects;{' '}
            {summary.drawable_count.toLocaleString()} drawable. Whole-study category counts
            (overlap):{' '}
            {layers
              .map((layer) => `${layer.label} ${summary.layer_counts[layer.key].toLocaleString()}`)
              .join(' · ')}
            .
          </p>
        )}
        </details>
        {enabled && summary?.verified && Object.keys(summary.diagnostics.counts).length > 0 && (
          <details>
            <summary>Source geometry diagnostics</summary>
            <p>
              {Object.entries(summary.diagnostics.counts)
                .map(([key, count]) => `${key}: ${count}`)
                .join(' · ')}
              . These objects remain in the source and can be inspected.
            </p>
            <div className="osm-object-list">
              {summary.diagnostics.samples.map((item) => (
                <button
                  type="button"
                  key={`${item.element_type}/${item.osm_id}`}
                  onClick={() =>
                    setSelection({
                      key: `${item.element_type}/${item.osm_id}`,
                      snapshot: identityKey(summary.identity),
                    })
                  }
                >
                  {item.element_type}/{item.osm_id} · {item.reason}
                </button>
              ))}
            </div>
            {!summary.diagnostics.samples_complete && (
              <p>Diagnostic samples are incomplete; use source export for all records.</p>
            )}
          </details>
        )}
        {view?.data.display.representation === 'detail' && view.data.features.length > 0 && (
          <details>
            <summary>Inspect visible objects (first 50)</summary>
            <p>
              Click any object on the map or choose one below. Selection clears when the view,
              categories or style change.
            </p>
            <div className="osm-object-list">
              {view.data.features.slice(0, 50).map((feature) => (
                <button
                  type="button"
                  key={objectKey(feature)}
                  onClick={() => setSelection({ key: objectKey(feature), snapshot: view.snapshot })}
                >
                  {objectKey(feature)}
                </button>
              ))}
            </div>
          </details>
        )}
      </fieldset>
      {enabled && selection && (
        <ObjectDetails
          key={`${selection.snapshot}:${selection.key}`}
          base={base}
          selection={selection}
          onClose={() => setSelection(null)}
        />
      )}
    </section>
  )
}

function ObjectDetails({
  base,
  selection,
  onClose,
}: {
  base: string
  selection: Selection
  onClose: () => void
}) {
  const [detail, setDetail] = useState<OsmObjectDetail | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const active = new AbortController()
    setDetail(null)
    setError('')
    getJson<OsmObjectDetail>(`${base}/features/${selection.key}`, active.signal)
      .then((value) => {
        if (active.signal.aborted) return
        if (identityKey(value.display.identity) !== selection.snapshot)
          throw new Error('The source changed. Refresh OSM before selecting this object again.')
        setDetail(value)
      })
      .catch((failure) => {
        if (!active.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'Cannot load object details.')
      })
    return () => active.abort()
  }, [base, selection.key, selection.snapshot, attempt])
  return (
    <section className="osm-details" aria-label="Selected OSM object">
      <h3>OSM {selection.key}</h3>
      <button type="button" onClick={onClose}>
        Close OSM details
      </button>
      {!detail && !error && <p role="status">Loading original object details…</p>}
      {error && (
        <>
          <p role="alert">{error}</p>
          <button type="button" onClick={() => setAttempt((value) => value + 1)}>
            Retry object details
          </button>
        </>
      )}
      {detail && (
        <>
          <p>
            Original source tags and geometry; categories:{' '}
            {detail.display.categories.join(', ') || 'none'}. Rule version:{' '}
            {detail.display.identity.rule_version}.
          </p>
          {detail.display.diagnostic && (
            <p>
              Geometry diagnostic: {detail.display.diagnostic}. Drawable:{' '}
              {String(detail.display.drawable)}.
            </p>
          )}
          {detail.display.geometry_omitted && (
            <p>
              Geometry omitted: {detail.display.geometry_omitted}. Tags and classification are
              available below.
            </p>
          )}
          <details open>
            <summary>Original tags</summary>
            <dl>
              {Object.entries(detail.properties).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{showValue(value)}</dd>
                </div>
              ))}
            </dl>
          </details>
          {layers.map(
            ({ key }) =>
              detail.layer_analyses?.[key] && (
                <CostDetails key={key} layer={key} analysis={detail.layer_analyses[key]!} />
              ),
          )}
        </>
      )}
    </section>
  )
}
