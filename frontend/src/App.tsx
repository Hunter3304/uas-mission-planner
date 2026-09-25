import { useCallback, useEffect, useMemo, useState } from 'react'
import { downloadDataset, getJson } from './api'
import MapCanvas from './MapCanvas'
import {
  featureKey,
  featureLayers,
  isVisible,
  layers,
  type Dataset,
  type MapData,
  type MapFeature,
  type Visibility,
} from './types'

const allVisible: Visibility = { building: true, highway: true, landuse: true, natural: true }
const dateText = (value: string | null) =>
  value
    ? new Date(value).toLocaleString('en-GB', {
        timeZone: 'UTC',
        dateStyle: 'medium',
        timeStyle: 'short',
      }) + ' UTC'
    : 'Not recorded'

export default function App() {
  const [catalog, setCatalog] = useState<Dataset[]>([])
  const [id, setId] = useState('')
  const [revision, setRevision] = useState(0)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState('')
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [data, setData] = useState<MapData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [visibility, setVisibility] = useState<Visibility>(allVisible)
  const [selected, setSelected] = useState<MapFeature | null>(null)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [downloading, setDownloading] = useState('')
  const [downloadStatus, setDownloadStatus] = useState('')
  const onSelect = useCallback((feature: MapFeature) => setSelected(feature), [])

  useEffect(() => {
    const controller = new AbortController()
    setCatalogLoading(true)
    setCatalogError('')
    getJson<{ datasets: Dataset[] }>('/api/datasets', controller.signal)
      .then((result) => {
        setCatalog(result.datasets)
        setId((current) =>
          result.datasets.some((item) => item.id === current)
            ? current
            : (result.datasets[0]?.id ?? ''),
        )
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setCatalogError(err.message || 'Cannot connect to the data service.')
          setCatalog([])
          setId('')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setCatalogLoading(false)
      })
    return () => controller.abort()
  }, [revision])

  useEffect(() => {
    const controller = new AbortController()
    setDataset(null)
    setData(null)
    setSelected(null)
    setError('')
    setSearch('')
    setPage(0)
    setDownloadStatus('')
    if (!id) {
      setLoading(false)
      return () => controller.abort()
    }
    setLoading(true)
    Promise.all([
      getJson<Dataset>(`/api/datasets/${encodeURIComponent(id)}`, controller.signal),
      getJson<MapData>(`/api/datasets/${encodeURIComponent(id)}/features`, controller.signal),
    ])
      .then(([info, features]) => {
        setDataset(info)
        setData(features)
        setVisibility(allVisible)
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [id, revision])

  const visible = useMemo(
    () => data?.features.filter((feature) => isVisible(feature, visibility)) ?? [],
    [data, visibility],
  )
  const filtered = useMemo(
    () =>
      visible.filter((feature) =>
        `${featureKey(feature)} ${String(feature.properties.name ?? '')}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [visible, search],
  )
  const pageCount = Math.max(1, Math.ceil(filtered.length / 8))
  const currentPage = Math.min(page, pageCount - 1)
  async function download(format: string) {
    setDownloading(format)
    setDownloadStatus('')
    try {
      await downloadDataset(id, format)
      setDownloadStatus('Download ready. Check your browser downloads.')
    } catch (err) {
      setDownloadStatus(err instanceof Error ? err.message : 'Download failed.')
    } finally {
      setDownloading('')
    }
  }

  return (
    <div className="app">
      <header className="header">
        <a className="brand" href="/" aria-label="UAS Mission Planner home">
          <span className="brand-mark">↗</span>
          <span>
            UAS <strong>Mission Planner</strong>
            <small>GEOSPATIAL RESEARCH WORKSPACE</small>
          </span>
        </a>
        <div className="header-right">
          <span className="nav-active">Dataset explorer</span>
          <span className="local-badge">
            <i /> Local workspace
          </span>
        </div>
      </header>
      <main className="workspace">
        <aside className="sidebar">
          <div className="section-kicker">WORKSPACE / 01</div>
          <h1>
            Explore your <br />
            map data.
          </h1>
          <p className="intro">Inspect the geography behind your next mission.</p>
          <section className="side-section">
            <div className="section-row">
              <h2>Saved dataset</h2>
              <button
                className="text-button"
                onClick={() => setRevision((value) => value + 1)}
                disabled={catalogLoading}
              >
                ↻ Refresh
              </button>
            </div>
            <label className="sr-only" htmlFor="dataset">
              Saved dataset
            </label>
            <select
              id="dataset"
              value={id}
              onChange={(event) => setId(event.target.value)}
              disabled={catalogLoading || !catalog.length}
            >
              {!catalog.length && (
                <option value="">
                  {catalogLoading ? 'Loading datasets…' : 'No saved datasets'}
                </option>
              )}
              {catalog.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.id}
                  {!item.verified ? ' · needs attention' : ''}
                </option>
              ))}
            </select>
            <p className="subtle">
              {catalog.length} saved dataset{catalog.length === 1 ? '' : 's'} · stored locally
            </p>
          </section>
          <section className="side-section">
            <div className="section-row">
              <h2>Map layers</h2>
              <span className="micro-label">
                {Object.values(visibility).filter(Boolean).length} / 4
              </span>
            </div>
            <div className="layer-list">
              {layers.map((layer) => (
                <label className="layer-row" key={layer.key}>
                  <input
                    type="checkbox"
                    checked={visibility[layer.key]}
                    disabled={!data}
                    onChange={(event) => {
                      setVisibility((current) => ({
                        ...current,
                        [layer.key]: event.target.checked,
                      }))
                      setPage(0)
                    }}
                  />
                  <span className="layer-swatch" style={{ background: layer.color }} />
                  <span>{layer.label}</span>
                  <strong>{dataset?.layer_counts[layer.key] ?? '—'}</strong>
                </label>
              ))}
            </div>
            <p className="subtle">Layers may overlap. Totals count each feature once.</p>
          </section>
          <section className="side-section export-section">
            <h2>Take your data further</h2>
            <p className="subtle">Download the complete dataset, including hidden layers.</p>
            <button
              className="primary-button"
              disabled={!dataset || !!downloading}
              onClick={() => download('geojson')}
            >
              {downloading === 'geojson' ? 'Preparing…' : '↓ Download GeoJSON'}
            </button>
            <div className="download-pair">
              <button disabled={!dataset || !!downloading} onClick={() => download('gpkg')}>
                GeoPackage ↓
              </button>
              <button disabled={!dataset || !!downloading} onClick={() => download('metadata')}>
                Metadata ↓
              </button>
            </div>
            {downloadStatus && (
              <p role="status" className="download-status">
                {downloadStatus}
              </p>
            )}
          </section>
          <div className="sidebar-foot">
            <span className="foot-line" />
            <strong>Built for informed planning</strong>
            <p>
              Open geographic data.
              <br />
              Reproducible research.
            </p>
          </div>
        </aside>
        <section className="content" aria-label="Dataset overview">
          <div className="page-heading">
            <div>
              <div className="section-kicker">DATASET EXPLORER</div>
              <h2>{id ? id.replaceAll('-', ' ') : 'Your geographic workspace'}</h2>
            </div>
            {dataset && <span className="verified-badge">✓ Integrity verified</span>}
          </div>
          {(catalogError || error) && (
            <div className="state-card error-state" role="alert">
              <h3>Unable to load this dataset</h3>
              <p>{catalogError || error}</p>
              <p>Check that the local API is running and the dataset files are available.</p>
              <button onClick={() => setRevision((value) => value + 1)}>Try again</button>
            </div>
          )}
          {(catalogLoading || loading) && (
            <div className="state-card" role="status">
              <span className="spinner" />
              <p>Loading your geographic data…</p>
            </div>
          )}
          {!catalogLoading && !catalogError && !catalog.length && (
            <div className="state-card">
              <h3>Your workspace is ready for data</h3>
              <p>
                Use the acquisition command in the README to save a dataset, then select Refresh.
              </p>
            </div>
          )}
          {dataset && data && !loading && !catalogLoading && !catalogError && (
            <>
              <div className="stats-grid">
                <article className="stat">
                  <span>Total features</span>
                  <strong data-testid="total-count">
                    {dataset.feature_count.toLocaleString()}
                  </strong>
                  <small>
                    {dataset.synthetic ? 'Synthetic sample objects' : 'Unique OSM objects'}
                  </small>
                </article>
                <article className="stat">
                  <span>Visible on map</span>
                  <strong data-testid="visible-count">
                    {visible.length.toLocaleString()}
                    <em> / {dataset.feature_count}</em>
                  </strong>
                  <small>Across active layers</small>
                </article>
                <article className="stat">
                  <span>Geometry mix</span>
                  <div className="geometry-stats">
                    {['Point', 'Line', 'Polygon'].map((name, index) => (
                      <div key={name}>
                        <strong>
                          {Object.entries(dataset.geometry_counts)
                            .filter(([type]) => type.includes(name))
                            .reduce((sum, [, count]) => sum + count, 0)}
                        </strong>
                        <small>{['Points', 'Lines', 'Polygons'][index]}</small>
                      </div>
                    ))}
                  </div>
                </article>
                <article className="stat">
                  <span>Query area</span>
                  <strong>
                    {dataset.query_area_km2?.toFixed(3) ?? '—'} <em>km²</em>
                  </strong>
                  <small>{dataset.crs}</small>
                </article>
              </div>
              <div className="map-title">
                <h3>Geographic overview</h3>
                <span>
                  <i /> Saved source data
                </span>
              </div>
              <MapCanvas
                dataset={dataset}
                data={data}
                visibility={visibility}
                onSelect={onSelect}
              />
              {!data.features.length && (
                <p className="empty-note" role="status">
                  No matching features in this dataset. The query boundary is shown for reference.
                </p>
              )}
              {data.features.length > 0 && !visible.length && (
                <p className="empty-note" role="status">
                  All layers are hidden. Enable a layer to show features.
                </p>
              )}
              <div className="detail-grid">
                <section className="feature-panel">
                  <div className="section-row">
                    <h3>
                      Feature browser <span className="count-pill">{filtered.length}</span>
                    </h3>
                    <input
                      aria-label="Search features"
                      className="search"
                      placeholder="Search name or OSM ID…"
                      value={search}
                      onChange={(event) => {
                        setSearch(event.target.value)
                        setPage(0)
                      }}
                    />
                  </div>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>OSM object</th>
                          <th>Layer</th>
                          <th>Name</th>
                          <th>Geometry</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.slice(currentPage * 8, currentPage * 8 + 8).map((feature) => (
                          <tr
                            key={featureKey(feature)}
                            className={
                              selected && featureKey(selected) === featureKey(feature)
                                ? 'selected-row'
                                : ''
                            }
                          >
                            <td>
                              <button className="feature-link" onClick={() => onSelect(feature)}>
                                {featureKey(feature)}
                              </button>
                            </td>
                            <td>
                              <span
                                className="feature-dot"
                                style={{ background: featureLayers(feature)[0]?.color }}
                              />
                              {featureLayers(feature)
                                .map((layer) => layer.label)
                                .join(', ')}
                            </td>
                            <td>{String(feature.properties.name ?? 'Unnamed')}</td>
                            <td>{feature.geometry.type}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!filtered.length && (
                    <p className="empty-note">No features match the active layers and search.</p>
                  )}
                  <div className="pagination">
                    <span>
                      Page {currentPage + 1} of {pageCount}
                    </span>
                    <div>
                      <button disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>
                        ← Previous
                      </button>
                      <button
                        disabled={currentPage + 1 >= pageCount}
                        onClick={() => setPage(currentPage + 1)}
                      >
                        Next →
                      </button>
                    </div>
                  </div>
                </section>
                <section className="inspector">
                  <div className="section-row">
                    <h3>Feature details</h3>
                    {selected && (
                      <button className="text-button" onClick={() => setSelected(null)}>
                        Clear
                      </button>
                    )}
                  </div>
                  {selected ? (
                    <>
                      <p className="selected-id">{featureKey(selected)}</p>
                      <dl className="properties">
                        {Object.entries(selected.properties)
                          .filter(([, value]) => value != null)
                          .map(([key, value]) => (
                            <div key={key}>
                              <dt>{key}</dt>
                              <dd>
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </dd>
                            </div>
                          ))}
                      </dl>
                    </>
                  ) : (
                    <div className="inspector-empty">
                      <span>⌖</span>
                      <p>
                        Select a feature on the map
                        <br />
                        or in the table to inspect its tags.
                      </p>
                    </div>
                  )}
                </section>
              </div>
              <footer className="data-footer">
                <span>
                  Source:{' '}
                  {dataset.synthetic
                    ? 'Synthetic demonstration sample'
                    : '© OpenStreetMap contributors'}
                </span>
                <span>Saved {dateText(dataset.saved_at_utc)}</span>
                <span>{dataset.invalid_geometry_count} invalid geometries recorded</span>
              </footer>
            </>
          )}
        </section>
      </main>
    </div>
  )
}
