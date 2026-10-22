import { expect, test, type Page, type Route } from '@playwright/test'

const bounds = { west: 9.79, south: 52.378, east: 9.81, north: 52.398 }
const identity = { schema_version: 2, source_sha256: 'selection-source', rule_version: 'selection-rules' }
const empty = { type: 'FeatureCollection', features: [] }
const geometry = { type: 'Polygon', coordinates: [[[9.799, 52.387], [9.801, 52.387], [9.801, 52.389], [9.799, 52.389], [9.799, 52.387]]] }
const point = { type: 'Feature', id: 'node/1', geometry: { type: 'Point', coordinates: [9.8, 52.388] }, properties: { element_type: 'node', osm_id: 1, categories: ['building'] } }
const polygon = { type: 'Feature', id: 'way/2', geometry, properties: { element_type: 'way', osm_id: 2, categories: ['landuse'] } }
function detail(id: string) {
  return { type: 'Feature', id, geometry: id === 'node/1' ? point.geometry : geometry, properties: { element_type: id.split('/')[0], osm_id: Number(id.split('/')[1]), name: id === 'node/1' ? 'First selected object' : '<script>Second selected object</script>' }, layer_analyses: {}, display: { identity, categories: ['building'], diagnostic: id === 'way/3' ? 'invalid_source_geometry' : null, drawable: id !== 'way/3', geometry_omitted: null } }
}
async function setup(page: Page, override?: (route: Route, path: string) => Promise<boolean>) {
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
const inspector = (page: Page) => page.getByRole('region', { name: 'Map object inspector', exact: true })
const osm = (page: Page) => page.getByRole('region', { name: 'Regional OSM display', exact: true })
const map = (page: Page) => page.getByRole('region', { name: 'Hannover regional map', exact: true })
const black = (page: Page) => map(page).locator('.leaflet-regional-selection-pane path[stroke="#000000"]')
async function centerClick(page: Page) {
  const box = await map(page).boundingBox()
  await map(page).click({ position: { x: box!.width / 2, y: box!.height / 2 } })
}
async function detailView(page: Page) {
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await osm(page).getByText('Inspect visible objects (first 50)', { exact: true }).click()
}

test('selection outlines preserve map layout, hit testing and focus; popup close and fold keep selection', async ({ page }) => {
  const { calls, errors } = await setup(page)
  await detailView(page)
  const originalMapY = await map(page).evaluate(element => element.getBoundingClientRect().top + scrollY)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page)).toContainText('First selected object')
  await expect(black(page)).toHaveCount(1)
  await expect(black(page)).toHaveAttribute('fill', 'none')
  expect(await black(page).evaluate(element => getComputedStyle(element).pointerEvents)).toBe('none')
  expect(await map(page).evaluate(element => element.getBoundingClientRect().top + scrollY)).toBe(originalMapY)
  const panelBox = await inspector(page).boundingBox(), mapBox = await map(page).boundingBox()
  expect(panelBox!.x + panelBox!.width).toBeLessThan(mapBox!.x)
  await map(page).locator('.leaflet-popup-close-button').click()
  await expect(inspector(page)).toContainText('First selected object')
  await expect(black(page)).toHaveCount(1)
  // Hide the other object so clicking through the outline selects the same point.
  await osm(page).getByLabel('Land use', { exact: true }).uncheck()
  await expect(page.getByTestId('osm-status')).toHaveText('1 individual OSM objects in the buffered viewport.')
  await osm(page).getByText('Inspect visible objects (first 50)', { exact: true }).click()
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(black(page)).toHaveCount(1)
  await centerClick(page)
  await expect(inspector(page)).toContainText('First selected object')
  const requestCount = calls.urls.length
  for (let i = 0; i < 10; i++) {
    await centerClick(page)
    await expect(black(page)).toHaveCount(1)
  }
  await inspector(page).getByRole('button', { name: 'Collapse object details' }).click()
  await page.getByRole('button', { name: 'View details', exact: true }).click()
  await expect(inspector(page)).toBeFocused()
  await expect(inspector(page).getByRole('button', { name: 'Collapse object details' })).toHaveAttribute('aria-expanded', 'true')
  expect(calls.urls.length).toBe(requestCount)
  await page.getByRole('button', { name: 'Collapse OSM', exact: true }).click()
  await expect(inspector(page)).toContainText('First selected object')
  await expect(black(page)).toHaveCount(1)
  await inspector(page).getByRole('button', { name: 'Clear selection', exact: true }).click()
  await expect(black(page)).toHaveCount(0)
  expect(errors).toEqual([])
})

test('OSM, DIPUL and GHSL replace one shared selection without extra loads; mobile uses one sheet', async ({ page }) => {
  const { calls, errors } = await setup(page)
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page)).toContainText('First selected object')
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await expect(black(page)).toHaveCount(0)
  await page.getByLabel('Scenario start', { exact: true }).fill('2026-10-07T10:00')
  await page.getByLabel('Scenario end', { exact: true }).fill('2026-10-07T10:15')
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  await centerClick(page)
  await expect(inspector(page)).toContainText('DIPUL · zone/1')
  await expect(black(page)).toHaveCount(1)
  const dipul = page.getByRole('region', { name: 'DIPUL restrictions', exact: true })
  await dipul.getByLabel('Policy exclusions').uncheck()
  await expect(black(page)).toHaveCount(0)
  await page.getByLabel('GHSL — population cells', { exact: true }).check()
  await expect(page.getByRole('region', { name: 'GHSL population', exact: true })).toContainText('Ready · 1 cells')
  await centerClick(page)
  await expect(inspector(page)).toContainText('Population: 0 people')
  await expect(black(page)).toHaveCount(1)
  await dipul.getByLabel('Policy exclusions').check()
  await centerClick(page)
  await expect(inspector(page)).toContainText('DIPUL · zone/1')
  await expect(inspector(page).getByRole('region', { name: 'Selected OSM object' })).toHaveCount(0)
  await expect(black(page)).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(inspector(page)).toBeVisible()
  expect(await inspector(page).evaluate(element => getComputedStyle(element).position)).toBe('fixed')
  expect((await inspector(page).boundingBox())!.height).toBeLessThanOrEqual(844 * .55 + 1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(page.getByRole('region', { name: 'Map object inspector', exact: true })).toHaveCount(1)
  expect(calls.constraints).toBe(1)
  expect(calls.urls.filter(url => url.includes('/study/population'))).toHaveLength(1)
  expect(calls.routes).toBe(0)
  expect(errors).toEqual([])
})

test('late original details cannot overwrite a new selection; geometry diagnostics have no invented outline', async ({ page }) => {
  let pending: Route | undefined
  await setup(page, async (route, path) => {
    if (path.endsWith('/study/osm/features/node/1')) { pending = route; return true }
    return false
  })
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect.poll(() => Boolean(pending)).toBe(true)
  await osm(page).getByRole('button', { name: 'way/2', exact: true }).click()
  await expect(inspector(page)).toContainText('<script>Second selected object</script>')
  await pending!.fulfill({ json: detail('node/1') }).catch(() => {})
  await expect(inspector(page)).not.toContainText('First selected object')
  await expect(black(page)).toHaveCount(1)
  await osm(page).getByText('Source geometry diagnostics', { exact: true }).click()
  await osm(page).getByRole('button', { name: /way\/3/ }).click()
  await expect(inspector(page)).toContainText('No drawable geometry')
  await expect(inspector(page)).toContainText('Drawable: false')
  await expect(black(page)).toHaveCount(0)
})

test('aggregate cells are labelled, zoom to objects, and object selection survives a small pan only while present', async ({ page }) => {
  const { calls } = await setup(page)
  await centerClick(page)
  await expect(inspector(page)).toContainText('Aggregate overview cell')
  await expect(black(page)).toHaveCount(1)
  await inspector(page).getByRole('button', { name: 'Zoom for objects', exact: true }).click()
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await expect(black(page)).toHaveCount(0)
  await osm(page).getByText('Inspect visible objects (first 50)', { exact: true }).click()
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page)).toContainText('First selected object')
  const originalDetails = calls.details.length
  const before = calls.urls.filter(url => /\/osm\/(summary|features\?)/.test(url)).length
  await map(page).focus(); await map(page).press('ArrowRight')
  await expect.poll(() => calls.urls.filter(url => /\/osm\/(summary|features\?)/.test(url)).length).toBeGreaterThan(before)
  await expect(page.getByTestId('osm-status')).not.toContainText('Loading')
  await expect(inspector(page)).toContainText('First selected object')
  expect(calls.details).toHaveLength(originalDetails)
  await page.getByRole('button', { name: 'Fit study', exact: true }).click()
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'aggregate_overview')
  await expect(black(page)).toHaveCount(0)
})

test('changed original identity clears selected geometry and reports the stale source', async ({ page }) => {
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/osm/features/node/1')) return false
    await route.fulfill({ json: { ...detail('node/1'), display: { ...detail('node/1').display, identity: { ...identity, source_sha256: 'replaced' } } } })
    return true
  })
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page).getByRole('alert')).toContainText('source changed')
  await expect(black(page)).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Selected OSM object', exact: true })).toHaveCount(0)
})

test('dataset refresh removes old selection and its popup without map cleanup errors', async ({ page }) => {
  const { errors } = await setup(page)
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page)).toContainText('First selected object')
  await page.getByRole('button', { name: '↻ Refresh', exact: true }).click()
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'aggregate_overview')
  await expect(inspector(page)).toContainText('Select an OSM object')
  await expect(black(page)).toHaveCount(0)
  await expect(map(page).locator('.selection-summary')).toHaveCount(0)
  expect(errors).toEqual([])
})

test('a changed display snapshot clears the old selection before replacement geometry arrives', async ({ page }) => {
  let replaced = false
  let pending: Route | undefined
  const nextIdentity = { ...identity, source_sha256: 'new-display-source' }
  await setup(page, async (route, path) => {
    if (!replaced) return false
    if (path.endsWith('/study/osm/summary')) {
      await route.fulfill({ json: { state: 'ready', verified: true, identity: nextIdentity, coverage_bounds: Object.values(bounds), feature_count: 1, drawable_count: 1, layer_counts: { building: 1, highway: 0, landuse: 0, natural: 0 }, diagnostics: { counts: {}, samples: [], samples_complete: true } } })
      return true
    }
    if (path.endsWith('/study/osm/features')) { pending = route; return true }
    return false
  })
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page)).toContainText('First selected object')
  replaced = true
  await map(page).focus(); await map(page).press('ArrowRight')
  await expect.poll(() => Boolean(pending)).toBe(true)
  await expect(black(page)).toHaveCount(0)
  await expect(inspector(page)).toContainText('Select an OSM object')
  await pending!.fulfill({ json: { type: 'FeatureCollection', features: [point], display: { identity: nextIdentity, representation: 'detail', complete: true, outside_coverage: false, returned_count: 1, style: 'category' } } })
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await expect(black(page)).toHaveCount(0)
})

for (const [name, shape, rings] of [
  ['line', { type: 'LineString', coordinates: [[9.799, 52.387], [9.8, 52.389], [9.801, 52.387]] }, 1],
  ['multipart with hole', { type: 'MultiPolygon', coordinates: [
    [[[9.799, 52.387], [9.801, 52.387], [9.801, 52.389], [9.799, 52.389], [9.799, 52.387]], [[9.7995, 52.3875], [9.7995, 52.3885], [9.8005, 52.3885], [9.8005, 52.3875], [9.7995, 52.3875]]],
    [[[9.803, 52.387], [9.804, 52.387], [9.804, 52.388], [9.803, 52.388], [9.803, 52.387]]],
  ] }, 3],
] as const) test(`selected ${name} follows original geometry instead of a bounding rectangle`, async ({ page }) => {
  await setup(page, async (route, path) => {
    if (path.endsWith('/study/osm/features')) {
      const feature = { ...polygon, id: 'relation/9', geometry: shape, properties: { element_type: 'relation', osm_id: 9, categories: ['building'] } }
      await route.fulfill({ json: { type: 'FeatureCollection', features: [feature], display: { identity, representation: 'detail', complete: true, outside_coverage: false, returned_count: 1, style: 'category' } } })
      return true
    }
    if (path.endsWith('/study/osm/features/relation/9')) { await route.fulfill({ json: { ...detail('relation/9'), geometry: shape } }); return true }
    return false
  })
  await detailView(page)
  await osm(page).getByRole('button', { name: 'relation/9', exact: true }).click()
  await expect(black(page)).toHaveCount(1)
  const path = await black(page).getAttribute('d')
  expect((path?.match(/M/g) ?? []).length).toBe(rings)
  if (name === 'line') expect(path).not.toMatch(/z/i)
})
