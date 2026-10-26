import { populationCosts } from './fixtures/populationCosts'
import { timedResult } from './fixtures/flightInterval'
import { expect, test, type Page, type Route } from '@playwright/test'

const bounds = { west: 9.7, south: 52.3, east: 9.9, north: 52.5 }
const ids = ['rheuma-podbi', 'mhh', 'henriettenstift', 'rheuma-lister', 'limbach-lehrte', 'amedes-georg', 'amedes-schiffgraben', 'friederikenstift']
const sites = ids.map((id, index) => ({ id, name: `Site ${id}`, longitude: 9.76 + index * .01, latitude: 52.38 }))
const empty = { type: 'FeatureCollection', features: [] }
const polygon = (source: string, category: string) => ({ type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[9.79, 52.37], [9.81, 52.37], [9.81, 52.39], [9.79, 52.39], [9.79, 52.37]]] }, properties: { source, category, state: 'unresolved' } })
const collection = (...features: ReturnType<typeof polygon>[]) => ({ type: 'FeatureCollection', features })
function layers() {
  return { blocked: collection(polygon('way/1', 'building_obstacle')), excluded: collection(polygon('dipul:test/1', 'conditional_zone')), unknown: collection(polygon('regional coverage', 'coverage'), polygon('way/2', 'building_obstacle'), polygon('notice/1', 'reviewed_notice')), allowed: empty, inactive: empty, diagnostics: [], interpretation: 'Fixture assessment', provenance: {} }
}
async function setup(page: Page, respond?: (route: Route, count: number) => Promise<void>) {
  const calls = { layers: [] as Record<string, unknown>[], routes: [] as Record<string, unknown>[], paths: [] as string[] }
  const dataset = { id: 'controls', has_study: true, verified: true, feature_count: 0, geometry_counts: {}, layer_counts: {}, crs: 'EPSG:4326', query_bounds: bounds, feature_bounds: null }
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    calls.paths.push(path)
    if (path.endsWith('/study/layers/constraints')) {
      calls.layers.push(route.request().postDataJSON())
      return respond ? respond(route, calls.layers.length) : route.fulfill({ json: layers() })
    }
    if (path.endsWith('/study/route')) {
      const body = route.request().postDataJSON(); calls.routes.push(body)
      return route.fulfill({ json: timedResult(route.request().postDataJSON(), { status: 'success', geometry: { type: 'LineString', coordinates: [body.start_coordinate ?? [9.76, 52.38], body.end_coordinate ?? [9.77, 52.38]] }, length_m: 1000, risk_length_cost: 20, objective_cost: 118, cruise_time_s: 1000 / 30, cruise_time_range_s: [1000 / 35, 40], preparation_ms: 20, planner_ms: 5, research_assumptions: [], endpoint_diagnostics: {} }) })
    }
    if (path.endsWith('/study')) return route.fulfill({ json: { config: { bounds, locations: sites }, sources: {} } })
    if (path === '/api/terrain-datasets') return route.fulfill({ json: { datasets: [{ id: 'hannover-part2-terrain-v1', tiles: 120 }] } })
    if (path.endsWith('/study/restriction-profiles')) return route.fulfill({ json: { profiles: [], errors: [] } })
    if (path.endsWith('/study/population-costs')) return route.fulfill({ json: populationCosts() })
    if (path.endsWith('/study/osm/summary')) return route.fulfill({ json: { state: 'not_prepared', verified: false } })
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : path.endsWith('/features') ? empty : dataset })
  })
  await page.goto('/')
  return calls
}
async function dates(page: Page) {
  await page.getByLabel('Departure time', { exact: true }).fill('2026-10-07T10:00')
}
const group = (page: Page, name: string) => page.getByRole('region', { name, exact: true })

test('first enable loads shared data; ten visibility and fold cycles use the cache', async ({ page }) => {
  const calls = await setup(page)
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Pending inputs')
  expect(calls.layers).toHaveLength(0)
  await dates(page)
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready · 1 features')
  await expect(page.getByTestId('osm-layer-state')).toContainText('Ready · 2 features')
  const dipul = group(page, 'DIPUL restrictions')
  const osm = group(page, 'OSM')
  await expect(group(page, 'Scenario coverage & diagnostics')).toHaveCount(0)
  for (let i = 0; i < 10; i++) {
    await dipul.getByLabel('Policy exclusions').uncheck()
    await dipul.getByLabel('Effective constraints').uncheck()
    await osm.getByLabel('Building obstacles').uncheck()
    await dipul.getByRole('button', { name: 'Collapse DIPUL restrictions' }).click()
    await dipul.getByRole('button', { name: 'Expand DIPUL restrictions' }).click()
    await dipul.getByLabel('Policy exclusions').check()
    await osm.getByLabel('Building obstacles').check()
    await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready · 1 features')
  }
  await dipul.getByLabel('Conditions satisfied').check()
  await page.waitForTimeout(450)
  expect(calls.layers).toHaveLength(1)
  expect(calls.routes).toHaveLength(0)
  expect(calls.paths.some(path => path.endsWith('/study/layers/zones'))).toBe(false)
  await expect(page.getByLabel('Original DIPUL')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Load scenario layers', exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Use explicitly selected launch/landing coordinates')).toHaveCount(0)
  await page.getByLabel('Altitude AGL').fill('110')
  await expect.poll(() => calls.layers.length).toBe(2)
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  await page.getByLabel('Objective', { exact: true }).selectOption('distance')
  await page.waitForTimeout(450)
  expect(calls.layers).toHaveLength(2)
})

test('one preparation at a time and late results cannot replace the newest scenario', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  const calls = await setup(page, async (route, count) => {
    if (count === 1) await gate
    await route.fulfill({ json: count === 1 ? layers() : { ...layers(), excluded: empty } })
  })
  await dates(page)
  await expect.poll(() => calls.layers.length).toBe(1)
  await page.getByLabel('Altitude AGL').fill('110')
  await page.getByLabel('Altitude AGL').fill('120')
  await page.waitForTimeout(450)
  expect(calls.layers).toHaveLength(1)
  release()
  await expect.poll(() => calls.layers.length).toBe(2)
  expect(calls.layers[1].scenario).toMatchObject({ agl_m: 120 })
  await expect(page.getByTestId('dipul-layer-state')).toContainText('No matching features')
  expect(calls.routes).toHaveLength(0)
})

test('a result finishing while hidden is retained; valid empty results are cached', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  const calls = await setup(page, async route => { await gate; await route.fulfill({ json: { ...layers(), excluded: empty } }) })
  await dates(page)
  await expect.poll(() => calls.layers.length).toBe(1)
  await group(page, 'OSM').getByLabel('Building obstacles').uncheck()
  const dipul = group(page, 'DIPUL restrictions')
  await dipul.getByLabel('Effective constraints').uncheck()
  await dipul.getByLabel('Policy exclusions').uncheck()
  release()
  await page.waitForTimeout(450)
  await dipul.getByLabel('Policy exclusions').check()
  await expect(page.getByTestId('dipul-layer-state')).toContainText('No matching features')
  await page.waitForTimeout(450)
  expect(calls.layers).toHaveLength(1)
})

test('failed preparation offers retry and is never cached as an empty success', async ({ page }) => {
  const calls = await setup(page, async (route, count) => route.fulfill(count === 1 ? { status: 422, json: { detail: 'Fixture preparation failed' } } : { json: layers() }))
  await dates(page)
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Fixture preparation failed')
  await page.getByRole('button', { name: 'Retry DIPUL scenario layers' }).click()
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready · 1 features')
  expect(calls.layers).toHaveLength(2)
})

test('GHSL cells remain cached across visibility and group folding without requiring a scenario', async ({ page }) => {
  const calls = await setup(page)
  const ghsl = group(page, 'GHSL population')
  await ghsl.getByLabel('GHSL — population risk (250 m)', { exact: true }).check()
  await expect(ghsl).toContainText('Ready · 1 cells')
  for (let i = 0; i < 3; i++) {
    await ghsl.getByLabel('GHSL — population risk (250 m)', { exact: true }).uncheck()
    await ghsl.getByRole('button', { name: 'Collapse GHSL population' }).click()
    await ghsl.getByRole('button', { name: 'Expand GHSL population' }).click()
    await ghsl.getByLabel('GHSL — population risk (250 m)', { exact: true }).check()
    await expect(ghsl).toContainText('Ready · 1 cells')
  }
  expect(calls.paths.filter(path => path.endsWith('/study/population-costs'))).toHaveLength(1)
  expect(calls.layers).toHaveLength(0)
  expect(calls.routes).toHaveLength(0)
})

test('endpoint modes have study bounds, active coordinates, isolated layout and matching export', async ({ page }) => {
  const calls = await setup(page)
  const panel = group(page, 'Regional route planning')
  await expect(panel.getByLabel('Selection method')).toHaveValue('sites')
  await expect(panel.getByLabel('Origin', { exact: true }).locator('option')).toHaveCount(8)
  await expect(panel.getByLabel('Destination', { exact: true }).locator('option')).toHaveCount(8)
  await expect(panel.getByLabel('Start longitude')).toHaveCount(0)
  await dates(page)
  await panel.getByLabel('Selection method').selectOption('coordinates')
  await expect(panel.getByLabel('Origin', { exact: true })).toHaveCount(0)
  await expect(panel.locator('#endpoint-bounds')).toContainText('longitude 9.7 to 9.9°; latitude 52.3 to 52.5°')
  await panel.getByLabel('Start longitude').fill('9.95')
  await expect(panel.locator('#start_lon-error')).toContainText('between 9.7 and 9.9')
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  expect(calls.routes).toHaveLength(0)
  for (const [label, value] of [['Start longitude', '9.78'], ['Start latitude', '52.4'], ['End longitude', '9.82'], ['End latitude', '52.41']]) await panel.getByLabel(label).fill(value)
  const endpointBox = await panel.locator('.endpoint-section').boundingBox()
  const parametersBox = await panel.locator('.regional-controls').boundingBox()
  expect(endpointBox!.y + endpointBox!.height).toBeLessThan(parametersBox!.y)
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  const map = group(page, 'Hannover regional map')
  await map.hover({ position: { x: (await map.boundingBox())!.width / 2, y: (await map.boundingBox())!.height / 2 } })
  await expect(map.locator('.leaflet-tooltip')).toContainText('Origin · Exact coordinates (9.78, 52.4)')
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('Length 1000.0 m')
  expect(calls.routes[0]).toMatchObject({ start_coordinate: [9.78, 52.4], end_coordinate: [9.82, 52.41] })
  const downloaded = page.waitForEvent('download')
  await panel.getByRole('button', { name: 'Export displayed result' }).click()
  const stream = await (await downloaded).createReadStream()
  let text = ''; for await (const chunk of stream!) text += chunk.toString()
  const exported = JSON.parse(text)
  expect(exported.features[0].geometry.coordinates).toEqual([[9.78, 52.4], [9.82, 52.41]])
  expect(exported.metadata.displayed_endpoint_selection.enabled).toBe(true)
  await panel.getByLabel('Selection method').selectOption('sites')
  await expect(panel.getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect.poll(() => calls.routes.length).toBe(2)
  expect(calls.routes[1]).not.toHaveProperty('start_coordinate')
  await page.setViewportSize({ width: 390, height: 844 })
  await panel.getByLabel('Selection method').selectOption('coordinates')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
