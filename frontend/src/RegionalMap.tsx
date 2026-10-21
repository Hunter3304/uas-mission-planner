import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import type { Feature, FeatureCollection, Geometry } from 'geojson'
import 'leaflet/dist/leaflet.css'
import { getJson } from './api'
import { populationColor } from './external'
import type { RestrictionReport } from './RestrictionProfiles'
import RegionalOsm from './RegionalOsm'

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
  zones: 'Original DIPUL — purple, applicability unverified',
  blocked: 'Effective constraints — red buffered footprints',
  excluded: 'Policy exclusions — orange, unresolved zones',
  allowed: 'Conditions satisfied — blue, scoped evidence',
  inactive: 'Not applicable — gray, scenario only',
  unknown: 'Unknown areas — amber buffered footprints',
  population: 'GHSL — people/native 100 m cell; white zero, pink NoData',
  route: 'Route — green, successful result only',
}
export default function RegionalMap({
  datasetId,
  study,
  startId,
  endId,
  geometry,
  constraints,
}: {
  datasetId: string
  study: Study | null
  startId: string
  endId: string
  geometry: Geometry | null
  constraints: ConstraintLayers | null
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const [readyMap, setReadyMap] = useState<L.Map | null>(null)
  const [visible, setVisible] = useState({
    boundary: true,
    locations: true,
    zones: false,
    blocked: true,
    excluded: true,
    allowed: false,
    inactive: false,
    unknown: false,
    population: false,
    route: true,
  })
  const [basemap, setBasemap] = useState(true)
  const [tileError, setTileError] = useState(false)
  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, { preferCanvas: true, zoomAnimation: false }).setView(
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
        const color = site.id === startId ? '#12664f' : site.id === endId ? '#c15733' : '#305fbc'
        const label = document.createElement('span')
        label.textContent = `${site.name} (${site.id})${site.id === startId ? ' · Origin' : ''}${site.id === endId ? ' · Destination' : ''}`
        L.circleMarker([site.latitude, site.longitude], { color, radius: 7, fillOpacity: 1 })
          .bindTooltip(label)
          .addTo(group)
      }
    return () => {
      group.remove()
    }
  }, [study, startId, endId, visible.boundary, visible.locations])
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
  return (
    <>
      <label>
        <input
          type="checkbox"
          checked={basemap}
          onChange={(event) => {
            setBasemap(event.target.checked)
            setTileError(false)
          }}
        />{' '}
        Street basemap — online OpenStreetMap tiles
      </label>
      {basemap && tileError && (
        <p role="alert">
          Street basemap tiles could not load. Check your internet connection; saved locations and
          data layers remain available.
        </p>
      )}
      <fieldset>
        <legend>Regional map layers</legend>
        {(Object.keys(legend) as (keyof typeof legend)[]).map((key) => (
          <label key={key} style={{ display: 'block' }}>
            <input
              type="checkbox"
              checked={visible[key]}
              onChange={(event) =>
                setVisible((current) => ({ ...current, [key]: event.target.checked }))
              }
            />{' '}
            {legend[key]}
          </label>
        ))}
      </fieldset>
      <div className="osm-selectors">
        {[
          { id: startId, label: 'Focus origin' },
          { id: endId, label: 'Focus destination' },
        ].map(({ id, label }) => (
          <button
            type="button"
            key={label}
            disabled={!study?.config.locations.some((site) => site.id === id)}
            onClick={() => {
              const site = study?.config.locations.find((item) => item.id === id)
              if (site)
                map.current?.setView([site.latitude, site.longitude], 16, { animate: false })
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {readyMap && (
        <>
          <RegionalOsm key={datasetId} map={readyMap} datasetId={datasetId} />
          <SourceOverlay
            key={`${datasetId}:zones`}
            map={readyMap}
            datasetId={datasetId}
            kind="zones"
            visible={visible.zones}
          />
          <SourceOverlay
            key={`${datasetId}:population`}
            map={readyMap}
            datasetId={datasetId}
            kind="population"
            visible={visible.population}
          />
          <GeoOverlay
            map={readyMap}
            collection={constraints?.blocked}
            visible={visible.blocked}
            color="#b33e39"
          />
          <GeoOverlay
            map={readyMap}
            collection={constraints?.unknown}
            visible={visible.unknown}
            color="#c87928"
          />
          <GeoOverlay
            map={readyMap}
            collection={constraints?.excluded}
            visible={visible.excluded}
            color="#df6800"
          />
          <GeoOverlay
            map={readyMap}
            collection={constraints?.allowed}
            visible={visible.allowed}
            color="#305fbc"
          />
          <GeoOverlay
            map={readyMap}
            collection={constraints?.inactive}
            visible={visible.inactive}
            color="#777777"
          />
        </>
      )}
      <div className="map-shell">
        <div
          className="map"
          style={{ minHeight: 480 }}
          ref={container}
          role="region"
          aria-label="Hannover regional map"
        />
      </div>
      <p>
        Saved source data:{' '}
        {study
          ? Object.values(study.sources)
              .map((source) => source.attribution)
              .filter(Boolean)
              .join(' · ')
          : 'Loading verified study…'}
        . GHSL is inspection only.
      </p>
      {!constraints && (
        <p>
          Effective constraints and unknown areas require an explicit scenario. Load scenario layers
          in the planning panel.
        </p>
      )}
      {constraints?.restriction_report && (
        <p>
          Zone decisions:{' '}
          {Object.entries(constraints.restriction_report.counts)
            .map(([key, value]) => `${key}: ${value}`)
            .join(' · ')}{' '}
          · Policy exclusions: {constraints.restriction_report.policy_exclusions ?? 0}. Coverage:{' '}
          {constraints.restriction_report.coverage.status}.
        </p>
      )}
      {constraints?.restriction_report?.building_counts && (
        <p>
          Original building records (separate from zones):{' '}
          {Object.entries(constraints.restriction_report.building_counts)
            .map(([key, value]) => `${key}: ${value}`)
            .join(' · ')}
          . Height estimates and derived geometry remain scenario assumptions.
        </p>
      )}
      {constraints && (
        <details>
          <summary>Layer coverage and applicability findings</summary>
          <p>{constraints.interpretation}</p>
          <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            {JSON.stringify(constraints.diagnostics, null, 2)}
          </pre>
        </details>
      )}
    </>
  )
}

function GeoOverlay({
  map,
  collection,
  visible,
  color,
  population = false,
}: {
  map: L.Map
  collection?: FeatureCollection
  visible: boolean
  color: string
  population?: boolean
}) {
  useEffect(() => {
    if (!visible || !collection) return
    const group = L.geoJSON(collection, {
      style: (feature) => ({
        color,
        weight: population ? 0.4 : 1.5,
        fillOpacity: population ? 0.55 : 0.2,
        fillColor: population ? populationColor(feature?.properties.people_per_cell) : undefined,
      }),
      onEachFeature: (feature, layer) =>
        layer.on('click', () => {
          const label = document.createElement('span')
          label.textContent = JSON.stringify(feature.properties)
          layer.bindPopup(label).openPopup()
        }),
    }).addTo(map)
    return () => {
      group.remove()
    }
  }, [map, collection, visible, color, population])
  return null
}

function SourceOverlay({
  map,
  datasetId,
  kind,
  visible,
}: {
  map: L.Map
  datasetId: string
  kind: 'zones' | 'population'
  visible: boolean
}) {
  const [collection, setCollection] = useState<FeatureCollection>()
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!visible || collection) return
    const active = new AbortController()
    setError('')
    const suffix = kind === 'zones' ? '/study/layers/zones' : '/study/population?cells=true'
    getJson<FeatureCollection | { layer: FeatureCollection }>(
      `/api/datasets/${encodeURIComponent(datasetId)}${suffix}`,
      active.signal,
    )
      .then((response) => {
        if (!active.signal.aborted) setCollection('layer' in response ? response.layer : response)
      })
      .catch((failure) => {
        if (!active.signal.aborted) setError(failure.message)
      })
    return () => active.abort()
  }, [datasetId, kind, visible, collection, attempt])
  return (
    <>
      <GeoOverlay
        map={map}
        collection={collection}
        visible={visible}
        color={kind === 'zones' ? '#8b5bb5' : '#527b66'}
        population={kind === 'population'}
      />
      {visible &&
        !collection &&
        (error ? (
          <p role="alert">
            {kind}: {error}{' '}
            <button type="button" onClick={() => setAttempt((value) => value + 1)}>
              Retry {kind}
            </button>
          </p>
        ) : (
          <p role="status">Loading {kind}…</p>
        ))}
    </>
  )
}
