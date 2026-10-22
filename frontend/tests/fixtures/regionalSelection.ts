import { expect, type Page, type Route } from '@playwright/test'

export const bounds = { west: 9.79, south: 52.378, east: 9.81, north: 52.398 }
export const identity = { schema_version: 2, source_sha256: 'selection-source', rule_version: 'selection-rules' }
export const empty = { type: 'FeatureCollection', features: [] }
export const geometry = { type: 'Polygon', coordinates: [[[9.799, 52.387], [9.801, 52.387], [9.801, 52.389], [9.799, 52.389], [9.799, 52.387]]] }
export const point = { type: 'Feature', id: 'node/1', geometry: { type: 'Point', coordinates: [9.8, 52.388] }, properties: { element_type: 'node', osm_id: 1, categories: ['building'] } }
export const polygon = { type: 'Feature', id: 'way/2', geometry, properties: { element_type: 'way', osm_id: 2, categories: ['landuse'] } }
export function detail(id: string) {
  return { type: 'Feature', id, geometry: id === 'node/1' ? point.geometry : geometry, properties: { element_type: id.split('/')[0], osm_id: Number(id.split('/')[1]), name: id === 'node/1' ? 'First selected object' : '<script>Second selected object</script>' }, layer_analyses: {}, display: { identity, categories: ['building'], diagnostic: id === 'way/3' ? 'invalid_source_geometry' : null, drawable: id !== 'way/3', geometry_omitted: null } }
}
export async function setup(page: Page, override?: (route: Route, path: string) => Promise<boolean>) {
  const calls = { urls: [] as string[], details: [] as string[], constraints: 0, routes: 0 }
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  const dataset = { id: 'selection', has_study: true, verified: true, feature_count: 2, geometry_counts: {}, layer_counts: {}, crs: 'EPSG:4326', query_bounds: bounds, feature_bounds: null }
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url()), path = url.pathname
    calls.urls.push(path + url.search)
    if (/\/study\/osm\/features\//.test(path)) calls.details.push(path)
    if (override && await override(route, path)) return
    if (path.endsWith('/study/osm/summary')) return route.fulfill({ json: { state: 'ready', verified: true, identity, coverage_bounds: Object.values(bounds), feature_count: 3, drawable_count: 2, layer_counts: { building: 1, highway: 0, landuse: 1, natural: 0 }, diagnostics: { counts: { invalid_source_geometry: 1 }, samples: [{ element_type: 'way', osm_id: 3, reason: 'invalid_source_geometry' }], samples_complete: true } } })
    if (/\/study\/osm\/features\//.test(path)) return route.fulfill({ json: detail(path.split('/').slice(-2).join('/')) })
    if (path.endsWith('/study/osm/overview') || path.endsWith('/study/osm/features')) {
      const overview = path.endsWith('/overview')
      const enabled = (url.searchParams.get('categories') ?? '').split(',')
      const features = overview ? [{ type: 'Feature', id: 'cell/1', geometry, properties: { objects: 2, category_counts: { building: 1, landuse: 1 } } }] : [point, polygon].filter(feature => feature.properties.categories.some(category => enabled.includes(category)))
      return route.fulfill({ json: { type: 'FeatureCollection', features, display: { identity, representation: overview ? 'aggregate_overview' : 'detail', returned_count: features.length, complete: true, outside_coverage: false, style: 'category' } } })
    }
    if (path.endsWith('/study/layers/constraints')) {
      calls.constraints++
      return route.fulfill({ json: { blocked: empty, unknown: empty, excluded: { type: 'FeatureCollection', features: [{ type: 'Feature', id: 'zone/1', geometry, properties: { source: 'dipul:test/1', category: 'conditional_zone', state: 'unresolved', reason: 'No scoped evidence' } }] }, diagnostics: [], provenance: {}, interpretation: 'Selection fixture' } })
    }
    if (path.endsWith('/study/population')) return route.fulfill({ json: { epoch: 2020, native_support_m: 100, layer: { type: 'FeatureCollection', features: [{ type: 'Feature', id: '10:20', geometry, properties: { people_per_cell: 0, epoch: 2020, native_support_m: 100 } }] } } })
    if (path.endsWith('/study/route')) { calls.routes++; return route.fulfill({ json: {} }) }
    if (path.endsWith('/study')) return route.fulfill({ json: { config: { bounds, locations: [{ id: 'rheuma-podbi', name: 'Origin', longitude: 9.8, latitude: 52.388 }, { id: 'mhh', name: 'Destination', longitude: 9.805, latitude: 52.388 }] }, sources: {} } })
    if (path === '/api/terrain-datasets') return route.fulfill({ json: { datasets: [{ id: 'hannover-part2-terrain-v1', tiles: 1 }] } })
    if (path.endsWith('/restriction-profiles')) return route.fulfill({ json: { profiles: [], errors: [] } })
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : path.endsWith('/features') ? empty : dataset })
  })
  await page.goto('/')
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'aggregate_overview')
  await page.getByLabel('Street basemap').uncheck()
  await page.getByLabel('Locations —').uncheck()
  return { calls, errors }
}
export const inspector = (page: Page) => page.getByRole('region', { name: 'Map object inspector', exact: true })
export const osm = (page: Page) => page.getByRole('region', { name: 'Regional OSM display', exact: true })
export const map = (page: Page) => page.getByRole('region', { name: 'Hannover regional map', exact: true })
export const black = (page: Page) => map(page).locator('.leaflet-regional-selection-pane path[stroke="#000000"]')
export async function centerClick(page: Page) {
  const box = await map(page).boundingBox()
  await map(page).click({ position: { x: box!.width / 2, y: box!.height / 2 } })
}
export async function detailView(page: Page) {
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await osm(page).getByText('Inspect visible objects (first 50)', { exact: true }).click()
}
