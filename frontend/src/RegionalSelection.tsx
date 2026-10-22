import { useCallback, useContext, useEffect, useMemo, useRef, useState, createContext, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import L from 'leaflet'
import OsmObjectDetails from './OsmObjectDetails'
import { MapSelectionContext, selectionFeatureId, type MapSelection, type SelectionActions } from './mapSelection'

const SelectedContext = createContext<MapSelection | null>(null)
const titleOf = (item: MapSelection) => String(item.feature.properties?.name ?? item.id)

export function MapSelectionProvider({ children }: { children: ReactNode }) {
  const [{ selected, notice }, setInspection] = useState<{ selected: MapSelection | null; notice: string }>({ selected: null, notice: '' })
  const [expanded, setExpanded] = useState(true)
  const inspector = useRef<HTMLElement>(null)
  const actions = useMemo<SelectionActions>(() => ({
    select: item => { setInspection({ selected: item, notice: '' }); setExpanded(true) },
    clear: () => { setInspection({ selected: null, notice: '' }) },
    reconcile: (owner, features, version) => setInspection(state => {
      const current = state.selected
      if (!current || current.owner !== owner) return state
      if (!features || current.version !== version) return { ...state, selected: null }
      const match = features.find(feature => selectionFeatureId(feature) === current.id)
      return match ? state : { ...state, selected: null }
    }),
    invalidate: (owner, id, version, message) => setInspection(state => {
      const current = state.selected
      if (!current || current.owner !== owner || current.id !== id || current.version !== version) return state
      return { selected: null, notice: message }
    }),
    showDetails: () => {
      setExpanded(true)
      inspector.current?.focus({ preventScroll: true })
    },
  }), [])
  const target = document.getElementById('regional-inspector')
  return <MapSelectionContext.Provider value={actions}>
    <SelectedContext.Provider value={selected}>{children}</SelectedContext.Provider>
    {target && createPortal(
      <section ref={inspector} tabIndex={-1} className={`regional-inspector ${selected ? 'has-selection' : 'selection-empty'}`} aria-label="Map object inspector">
        <div className="regional-inspector-heading">
          <h3>Object details</h3>
          {selected && <span className="selection-badge">Selected · {selected.source}</span>}
        </div>
        {selected ? <>
          <h4 className="selection-title">{titleOf(selected)}</h4>
          <div className="selection-actions">
            <button type="button" onClick={actions.clear}>Clear selection</button>
            <button type="button" aria-expanded={expanded} aria-controls="regional-inspector-content" onClick={() => setExpanded(value => !value)}>{expanded ? 'Collapse object details' : 'Expand object details'}</button>
          </div>
          <div id="regional-inspector-content" className="regional-inspector-content" hidden={!expanded}>
            {!selected.feature.geometry && <p>No drawable geometry is available for this object. No outline is drawn.</p>}
            {selected.osm ? <OsmObjectDetails key={`${selected.osm.snapshot}:${selected.osm.key}`} base={selected.osm.base} selection={selected.osm} /> : <>
              <p>{selected.source} · {selected.id}</p>
              {selected.aggregate ? <>
                <p>Aggregate overview cell · {String(selected.feature.properties?.objects ?? 'Unknown')} assigned objects. This is not an individual OSM object or a cost score.</p>
                <dl>{Object.entries(selected.feature.properties?.category_counts ?? {}).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}</dl>
                <button type="button" onClick={selected.zoom}>Zoom for objects</button>
              </> : <>
                {selected.feature.properties?.state != null && <p>Status: {String(selected.feature.properties.state)}</p>}
                {selected.feature.properties?.reason != null && <p>{String(selected.feature.properties.reason)}</p>}
                {selected.source === 'GHSL' && <p>Population: {selected.feature.properties?.people_per_cell == null ? 'NoData' : String(selected.feature.properties.people_per_cell)} people per native cell.</p>}
                <details open><summary>Original attributes</summary><dl>{Object.entries(selected.feature.properties ?? {}).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === 'object' && value != null ? JSON.stringify(value) : String(value ?? 'Not supplied')}</dd></div>)}</dl></details>
              </>}
            </>}
          </div>
        </> : <><p>Select an OSM object, population cell or constraint area on the map.</p>{notice && <p role="alert">{notice}</p>}</>}
      </section>, target)}
  </MapSelectionContext.Provider>
}

export function SelectionOverlay({ map }: { map: L.Map }) {
  const selected = useContext(SelectedContext)
  const actions = useContext(MapSelectionContext)!
  const clearOutside = useCallback(() => {
    if (!selected?.feature.geometry) return
    const bounds = L.geoJSON(selected.feature).getBounds()
    if (bounds.isValid() && !map.getBounds().intersects(bounds)) actions.clear()
  }, [map, selected, actions])
  useEffect(() => {
    map.on('moveend', clearOutside)
    return () => { map.off('moveend', clearOutside) }
  }, [map, clearOutside])
  useEffect(() => {
    if (!selected?.feature.geometry) return
    const pane = map.getPane('regional-selection') ?? map.createPane('regional-selection')
    pane.style.zIndex = '625'
    pane.style.pointerEvents = 'none'
    const renderer = L.svg({ pane: 'regional-selection' })
    const group = L.layerGroup().addTo(map)
    for (const [color, weight, radius] of [['#ffffff', 8, 10], ['#000000', 4, 7]] as const)
      L.geoJSON(selected.feature, {
        interactive: false,
        style: { color, weight, fill: false, renderer, interactive: false },
        pointToLayer: (_, latlng) => L.circleMarker(latlng, { color, weight, radius, fill: false, renderer, interactive: false }),
      }).addTo(group)
    const content = document.createElement('div')
    const title = document.createElement('strong')
    title.textContent = `${selected.source} · ${selected.aggregate ? 'Aggregate overview' : titleOf(selected)}`
    content.append(title)
    const description = document.createElement('p')
    const p = selected.feature.properties ?? {}
    const counts = Object.entries(p.category_counts ?? {}).map(([key, value]) => `${key}: ${value}`).join(' · ')
    description.textContent = selected.aggregate ? `${p.objects ?? 'Unknown'} assigned objects. ${counts}. Zoom for individual objects.` : selected.source === 'GHSL' ? `Population: ${p.people_per_cell ?? 'NoData'} per native cell` : String(p.state ?? selected.id)
    content.append(description)
    const button = document.createElement('button')
    button.type = 'button'
    button.textContent = 'View details'
    button.addEventListener('click', actions.showDetails)
    content.append(button)
    const bounds = L.geoJSON(selected.feature).getBounds()
    const desired = map.latLngToContainerPoint(selected.anchor ?? bounds.getCenter())
    const size = map.getSize()
    const margin = Math.min(140, size.x / 2)
    const anchor = map.containerPointToLatLng(L.point(
      Math.max(margin, Math.min(size.x - margin, desired.x)),
      Math.max(Math.min(140, size.y / 2), Math.min(size.y - 24, desired.y)),
    ))
    const popup = L.popup({ autoPan: false, maxWidth: 260, className: 'selection-summary' }).setLatLng(anchor).setContent(content).openOn(map)
    return () => {
      button.removeEventListener('click', actions.showDetails)
      map.closePopup(popup)
      group.clearLayers(); group.remove(); renderer.remove()
    }
  }, [map, selected, actions])
  return null
}
