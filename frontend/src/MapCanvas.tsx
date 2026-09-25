import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {
  featureKey,
  featureLayers,
  isVisible,
  type Dataset,
  type MapData,
  type MapFeature,
  type Visibility,
} from './types'

interface Props {
  dataset: Dataset
  data: MapData
  visibility: Visibility
  onSelect: (feature: MapFeature) => void
}

export default function MapCanvas({ dataset, data, visibility, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const [basemap, setBasemap] = useState(true)
  const [tileError, setTileError] = useState(false)
  const fit = () => {
    const b = dataset.feature_bounds
    const q = dataset.query_bounds
    map.current?.fitBounds(
      b
        ? [
            [b[1], b[0]],
            [b[3], b[2]],
          ]
        : [
            [q.south, q.west],
            [q.north, q.east],
          ],
      { padding: [35, 35], maxZoom: 18 },
    )
  }

  useEffect(() => {
    if (!container.current) return
    const instance = L.map(container.current, { zoomControl: false }).setView([52.27, 10.52], 15)
    map.current = instance
    L.control.zoom({ position: 'bottomright' }).addTo(instance)
    L.control.scale({ position: 'bottomleft', imperial: false }).addTo(instance)
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
    setTileError(false)
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map.current)
    tiles.on('tileerror', () => setTileError(true))
    return () => {
      tiles.remove()
    }
  }, [basemap])

  useEffect(() => {
    if (!map.current) return
    const attribution = dataset.synthetic
      ? 'Synthetic demonstration vectors'
      : 'Vector data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
    map.current.attributionControl.addAttribution(attribution)
    const q = dataset.query_bounds
    const query = L.rectangle(
      [
        [q.south, q.west],
        [q.north, q.east],
      ],
      {
        color: '#183e43',
        weight: 1.5,
        dashArray: '6 6',
        fill: false,
        interactive: false,
      },
    ).addTo(map.current)
    const b = dataset.feature_bounds
    map.current.fitBounds(
      b
        ? [
            [b[1], b[0]],
            [b[3], b[2]],
          ]
        : [
            [q.south, q.west],
            [q.north, q.east],
          ],
      { padding: [35, 35], maxZoom: 18 },
    )
    return () => {
      query.remove()
      map.current?.attributionControl.removeAttribution(attribution)
    }
  }, [dataset])

  useEffect(() => {
    if (!map.current) return
    const color = (feature: MapFeature) =>
      featureLayers(feature).find(({ key }) => visibility[key])?.color ?? '#7c8b91'
    const overlay = L.geoJSON(data, {
      filter: (feature) => isVisible(feature as MapFeature, visibility),
      style: (feature) => ({ color: color(feature as MapFeature), weight: 3, fillOpacity: 0.25 }),
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 5,
          color: '#fff',
          weight: 1.5,
          fillColor: color(feature as MapFeature),
          fillOpacity: 0.95,
        }),
      onEachFeature: (raw, layer) => {
        const feature = raw as MapFeature
        const label = document.createElement('span')
        label.textContent = String(feature.properties.name ?? featureKey(feature))
        layer.bindTooltip(label)
        layer.on('click', () => onSelect(feature))
      },
    }).addTo(map.current)
    return () => {
      overlay.remove()
    }
  }, [data, visibility, onSelect])

  return (
    <div className="map-shell">
      <div className="map" ref={container} role="region" aria-label="Dataset map" />
      <div className="map-tools">
        <label className="map-chip">
          <input
            type="checkbox"
            checked={basemap}
            onChange={(event) => setBasemap(event.target.checked)}
          />{' '}
          Basemap
        </label>
        <button className="map-chip" onClick={fit}>
          ↗ Fit dataset
        </button>
      </div>
      <div className="map-caption">
        <span className="dashed-line" /> Query boundary <span className="caption-divider">/</span>{' '}
        Complete source geometries
      </div>
      {tileError && basemap && (
        <div className="map-notice" role="status">
          Basemap unavailable. Your saved data is still visible.
        </div>
      )}
    </div>
  )
}
