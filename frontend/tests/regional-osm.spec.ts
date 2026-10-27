import { timedResult } from './fixtures/flightInterval'
import { expect, test, type Page, type Route } from '@playwright/test'

const identity = {
  schema_version: 2,
  source_sha256: 'fixture-source',
  rule_version: 'fixture-rules',
}
const bounds = { west: 9.79, south: 52.378, east: 9.81, north: 52.398 }
const dataset = {
  id: 'regional-osm',
  has_study: true,
  verified: true,
  feature_count: 2,
  geometry_counts: {},
  layer_counts: {},
  crs: 'EPSG:4326',
  query_bounds: bounds,
  feature_bounds: null,
}
const point = {
  type: 'Feature',
  id: 'node/1',
  geometry: { type: 'Point', coordinates: [9.8, 52.388] },
  properties: { element_type: 'node', osm_id: 1, categories: ['building', 'natural'] },
}
function summary() {
  return {
    state: 'ready',
    verified: true,
    identity,
    coverage_bounds: Object.values(bounds),
    feature_count: 2,
    drawable_count: 1,
    layer_counts: { building: 1, highway: 0, landuse: 0, natural: 1 },
    diagnostics: {
      counts: { invalid_source_geometry: 1 },
      samples: [{ element_type: 'way', osm_id: 2, reason: 'invalid_source_geometry' }],
      samples_complete: true,
    },
  }
}
function collection(overview: boolean, cost = false) {
  return {
    type: 'FeatureCollection',
    features: overview
      ? [
          {
            type: 'Feature',
            id: 'cell/1',
            geometry: {
              type: 'Polygon',
              coordinates: [
                [
                  [9.799, 52.387],
                  [9.801, 52.387],
                  [9.801, 52.389],
                  [9.799, 52.389],
                  [9.799, 52.387],
                ],
              ],
            },
            properties: { objects: 1, category_counts: { building: 1, natural: 1 } },
          },
        ]
      : [
          {
            ...point,
            ...(cost
              ? {
                  cost_analysis: {
                    cost: 4,
                    has_default: true,
                    obstruction: true,
                    status: 'default',
                  },
                }
              : {}),
          },
        ],
    display: {
      identity,
      representation: overview ? 'aggregate_overview' : 'detail',
      returned_count: 1,
      complete: true,
      outside_coverage: false,
      style: cost ? 'cost' : 'category',
    },
  }
}
function detail(id: string) {
  return {
    ...point,
    id,
    properties: {
      element_type: id.split('/')[0],
      osm_id: Number(id.split('/')[1]),
      building: 'hospital',
      name: '<script>unsafe tag</script>',
    },
    layer_analyses: {
      building: {
        cost: 4,
        has_default: false,
        obstruction: false,
        status: 'known',
        label: 'Very high',
        rule_version: 'fixture-rules',
        tags: [],
      },
    },
    display: {
      identity,
      representation: 'object_detail',
      categories: ['building'],
      diagnostic: id === 'way/2' ? 'invalid_source_geometry' : null,
      drawable: id !== 'way/2',
      geometry_omitted: null,
    },
  }
}

async function setup(page: Page, override?: (route: Route, url: URL) => Promise<boolean>) {
  const urls: string[] = []
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    urls.push(url.pathname + url.search)
    if (override && (await override(route, url))) return
    if (url.pathname.endsWith('/study/osm/summary')) return route.fulfill({ json: summary() })
    if (/\/study\/osm\/features\//.test(url.pathname))
      return route.fulfill({ json: detail(url.pathname.split('/').slice(-2).join('/')) })
    if (url.pathname.endsWith('/study/osm/overview'))
      return route.fulfill({ json: collection(true) })
    if (url.pathname.endsWith('/study/osm/features'))
      return route.fulfill({ json: collection(false, url.searchParams.get('style') === 'cost') })
    if (url.pathname.endsWith('/study/route'))
      return route.fulfill({
        json: timedResult(route.request().postDataJSON(), {
          status: 'success',
          geometry: {
            type: 'LineString',
            coordinates: [
              [9.795, 52.388],
              [9.805, 52.388],
            ],
          },
          length_m: 1000,
          risk_length_cost: 20,
          objective_cost: 118,
          cruise_time_s: 33.3,
          cruise_time_range_s: [28.6, 40],
          preparation_ms: 20,
          planner_ms: 5,
          research_assumptions: [],
          endpoint_diagnostics: {},
          provenance: { signature: 'fixture' },
        }),
      })
    if (url.pathname.endsWith('/study'))
      return route.fulfill({
        json: {
          config: {
            bounds,
            locations: [
              { id: 'rheuma-podbi', name: 'Podbi', longitude: 9.795, latitude: 52.388 },
              { id: 'mhh', name: 'MHH', longitude: 9.805, latitude: 52.388 },
            ],
          },
          sources: {},
        },
      })
    return route.fulfill({
      json:
        url.pathname === '/api/datasets'
          ? { datasets: [dataset] }
          : url.pathname === '/api/terrain-datasets'
            ? { datasets: [] }
            : dataset,
    })
  })
  await page.goto('/')
  return urls
}
const osm = (page: Page) => page.getByRole('region', { name: 'Regional OSM display', exact: true })
async function zoomDetail(page: Page) {
  const map = page.getByRole('region', { name: 'Hannover regional map' })
  for (let i = 0; i < 3; i++) await map.getByRole('button', { name: 'Zoom in' }).click()
  await expect(osm(page).getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
}

test('overview, category colors, original tags and independent route updates', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  const urls = await setup(page)
  const panel = osm(page)
  await expect(panel.getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  await expect(panel).toContainText('2 original objects; 1 drawable')
  expect(urls).toContain('/api/datasets/regional-osm/study?catalog_only=true')
  expect(urls).not.toContain('/api/datasets/regional-osm/study')
  expect(urls.some((url) => url === '/api/datasets/regional-osm/features')).toBe(false)
  await page.getByLabel('Street basemap').uncheck()
  await zoomDetail(page)
  await expect(panel.getByRole('combobox')).toHaveCount(0)
  await expect.poll(() => urls.some((url) => /osm\/features\?.*style=category/.test(url))).toBe(true)
  await expect(panel.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await expect(panel.getByLabel('OSM legend')).toContainText('Buildings')
  const map = page.getByRole('region', { name: 'Hannover regional map' })
  const box = await map.boundingBox()
  await map.click({ position: { x: box!.width / 2, y: box!.height / 2 } })
  const details = page.getByRole('region', { name: 'Selected OSM object' })
  await expect(details).toContainText('<script>unsafe tag</script>')
  await expect(details).toContainText('Building cost: 4')
  const before = urls.filter((url) => /\/osm\/(summary|features|overview)/.test(url)).length
  const canvas = await map.locator('.leaflet-overlay-pane canvas').elementHandle()
  const routing = page.getByRole('region', { name: 'Regional route planning' })
  await routing.getByLabel('Departure time').fill('2026-10-07T10:00')
  await routing.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(routing.getByRole('status')).toContainText('Length 1000.0 m')
  await expect(details).toContainText('node/1')
  await expect(map.locator('.leaflet-regional-route-pane svg')).toBeAttached()
  expect(await canvas!.evaluate((element) => element.isConnected)).toBe(true)
  expect(urls.filter((url) => /\/osm\/(summary|features|overview)/.test(url)).length).toBe(before)
  await page.getByRole('button', { name: 'Clear selection', exact: true }).click()
  await map.click({ position: { x: box!.width / 2, y: box!.height / 2 } })
  await expect(details).toContainText('Building cost: 4')
  await panel.getByLabel('Buildings', { exact: true }).uncheck()
  await expect.poll(() => urls.some(value => {
    const url = new URL(value, 'http://localhost')
    return url.pathname.endsWith('/osm/features') && url.searchParams.get('categories') === 'highway,landuse,natural' && url.searchParams.get('style') === 'category'
  })).toBe(true)
  await expect(page.getByRole('region', { name: 'Selected OSM object' })).toHaveCount(0)
  await expect(routing.getByRole('button', { name: 'Export displayed result' })).toBeVisible()
  await expect(panel.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  expect(urls.some(url => /style=cost|cost_category=/.test(url))).toBe(false)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(errors).toEqual([])
})

test('bounded detail falls back to labelled overview; diagnostic originals remain inspectable', async ({
  page,
}) => {
  await setup(page, async (route, url) => {
    if (!url.pathname.endsWith('/study/osm/features')) return false
    const data = collection(false)
    data.display.complete = false
    await route.fulfill({
      json: { ...data, display: { ...data.display, limit_reason: 'feature_limit' } },
    })
    return true
  })
  await expect(osm(page).getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  for (let i = 0; i < 3; i++)
    await page
      .getByRole('region', { name: 'Hannover regional map' })
      .getByRole('button', { name: 'Zoom in' })
      .click()
  await expect(osm(page)).toContainText('feature_limit')
  await expect(osm(page).getByTestId('osm-status')).toHaveAttribute(
    'data-representation',
    'aggregate_overview',
  )
  await expect(
    osm(page).getByText('Inspect visible objects (first 50)', { exact: true }),
  ).toHaveCount(0)
  await osm(page).getByText('Source geometry diagnostics', { exact: true }).click()
  await osm(page)
    .getByRole('button', { name: /way\/2/ })
    .click()
  await expect(page.getByRole('region', { name: 'Selected OSM object' })).toContainText(
    'Drawable: false',
  )
})

test('readiness, structured capacity errors, retry and snapshot mismatch never masquerade as empty', async ({
  page,
}) => {
  let state = 'not_prepared'
  await setup(page, async (route, url) => {
    if (url.pathname.endsWith('/study/osm/summary') && state === 'not_prepared') {
      await route.fulfill({
        json: { state, verified: false, message: 'Run study-osm-prepare explicitly.' },
      })
      return true
    }
    if (url.pathname.endsWith('/study/osm/overview') && state === 'busy') {
      await route.fulfill({
        status: 503,
        json: { detail: { state: 'busy', message: 'Query capacity reached; retry.' } },
      })
      return true
    }
    if (url.pathname.endsWith('/study/osm/overview') && state === 'mismatch') {
      const data = collection(true)
      data.display.identity = { ...identity, source_sha256: 'new-source' }
      await route.fulfill({ json: data })
      return true
    }
    return false
  })
  await expect(osm(page).getByRole('alert')).toContainText('not_prepared')
  state = 'busy'
  await osm(page).getByRole('button', { name: 'Refresh OSM', exact: true }).click()
  await expect(osm(page).getByRole('alert')).toContainText('Query capacity reached')
  state = 'mismatch'
  await osm(page).getByRole('button', { name: 'Refresh OSM', exact: true }).click()
  await expect(osm(page).getByRole('alert')).toContainText('snapshot changed')
  state = 'ready'
  await osm(page).getByRole('button', { name: 'Refresh OSM', exact: true }).click()
  await expect(osm(page).getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await expect(osm(page).getByTestId('osm-status')).toContainText('off')
  await expect(page.locator('.leaflet-overlay-pane canvas')).toHaveCount(1)
})

test('obsolete requests, empty view, category changes and outside coverage', async ({ page }) => {
  let pending: Route | undefined
  let delay = true
  let empty = false
  const urls = await setup(page, async (route, url) => {
    if (url.pathname.endsWith('/study/osm/features') && delay) {
      delay = false
      pending = route
      return true
    }
    if (url.pathname.endsWith('/study/osm/features') && empty) {
      const data = collection(false)
      await route.fulfill({
        json: { ...data, features: [], display: { ...data.display, returned_count: 0 } },
      })
      return true
    }
    return false
  })
  await expect(osm(page).getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  for (let i = 0; i < 3; i++)
    await page
      .getByRole('region', { name: 'Hannover regional map' })
      .getByRole('button', { name: 'Zoom in' })
      .click()
  await expect.poll(() => Boolean(pending)).toBe(true)
  await osm(page).getByLabel('Roads & paths', { exact: true }).uncheck()
  await expect(osm(page).getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await pending!.fulfill({ json: collection(false) }).catch(() => {})
  await expect(osm(page).getByLabel('OSM legend')).toContainText('Buildings')
  empty = true
  await osm(page).getByRole('button', { name: 'Refresh OSM', exact: true }).click()
  await expect(osm(page).getByTestId('osm-status')).toContainText('No matching OSM objects')
  for (const label of ['Buildings', 'Roads & paths', 'Land use', 'Natural features'])
    await osm(page).getByLabel(label, { exact: true }).uncheck()
  await expect(osm(page).getByTestId('osm-status')).toContainText('All OSM categories are hidden')
  await osm(page).getByLabel('Buildings', { exact: true }).check()
  await expect(osm(page).getByTestId('osm-status')).toContainText('No matching OSM objects')
  const map = page.getByRole('region', { name: 'Hannover regional map' })
  await map.focus()
  for (let i = 0; i < 12; i++) {
    await map.press('Shift+ArrowRight')
    await page.waitForTimeout(300)
  }
  await expect(osm(page).getByTestId('osm-status')).toContainText('Outside saved OSM coverage')
  expect(urls.every((url) => !url.endsWith('/regional-osm/features'))).toBe(true)
})

test('cached views still recheck readiness; closing details rejects late original-object responses', async ({
  page,
}) => {
  let ready = true
  let pending: Route | undefined
  const urls = await setup(page, async (route, url) => {
    if (url.pathname.endsWith('/study/osm/summary') && !ready) {
      await route.fulfill({
        json: { state: 'stale', verified: false, message: 'Source changed; prepare it again.' },
      })
      return true
    }
    if (url.pathname.endsWith('/study/osm/features/node/1')) {
      pending = route
      return true
    }
    return false
  })
  const panel = osm(page)
  await expect(panel.getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  const before = urls.filter((url) => url.includes('/osm/overview')).length
  await panel.getByLabel('Show saved OSM').uncheck()
  await panel.getByLabel('Show saved OSM').check()
  await expect(panel.getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  expect(urls.filter((url) => url.includes('/osm/overview')).length).toBe(before)
  ready = false
  await panel.getByLabel('Show saved OSM').uncheck()
  await panel.getByLabel('Show saved OSM').check()
  await expect(panel.getByRole('alert')).toContainText('Source changed')
  await expect(panel).not.toContainText('Verified saved study')
  ready = true
  await panel.getByRole('button', { name: 'Refresh OSM', exact: true }).click()
  await expect(panel.getByTestId('osm-status')).toContainText('Aggregate OSM overview')
  await zoomDetail(page)
  await panel.getByText('Inspect visible objects (first 50)', { exact: true }).click()
  await panel.getByRole('button', { name: 'node/1', exact: true }).click()
  await expect.poll(() => Boolean(pending)).toBe(true)
  await page.getByRole('button', { name: 'Clear selection', exact: true }).click()
  await pending!.fulfill({ json: detail('node/1') }).catch(() => {})
  await expect(page.getByRole('region', { name: 'Selected OSM object' })).toHaveCount(0)
})
