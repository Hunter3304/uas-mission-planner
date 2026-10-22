// Run against isolated current-code servers; no acquisition or source edits.
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createReadStream } from 'node:fs'
import { createHash } from 'node:crypto'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const require = createRequire(resolve(root, 'frontend/package.json'))
const { chromium, expect: baseExpect } = require('@playwright/test')
const expect = baseExpect.configure({ timeout: 180_000 })
const output = resolve(root, process.argv[2] ?? '.cache/iteration012-part3-ui')
await mkdir(output)
async function sha(path) {
  const hash = createHash('sha256')
  for await (const chunk of createReadStream(path)) hash.update(chunk)
  return hash.digest('hex')
}
const source = resolve(root, 'data/hannover-part1-v4/osm/features.gpkg')
const originalHash = await sha(source)
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(180_000)
  const errors = [], requests = [], responses = [], pending = [], datasetRequests = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    if (/\/study\/osm\//.test(request.url())) requests.push(request.url())
    if (/\/api\/datasets\//.test(request.url())) datasetRequests.push(request.url())
  })
  page.on('response', response => {
    if (!/\/study\/osm\//.test(response.url()) || !response.ok()) return
    pending.push((async () => {
      try {
        const body = await response.body()
        const data = JSON.parse(body.toString())
        responses.push({ url: response.url(), bytes: body.length, representation: data.display?.representation ?? data.state,
          count: data.features?.length, complete: data.display?.complete, identity: data.display?.identity ?? data.identity,
          sample: data.features?.slice(0, 5).map(feature => ({ id: feature.id, categories: feature.properties.categories, cost_analysis: feature.cost_analysis })) })
      } catch { /* a deliberately canceled response need not complete */ }
    })())
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.goto(process.env.UAS_UI_URL ?? 'http://127.0.0.1:5182')
  await expect(page.getByLabel('Saved dataset')).toBeEnabled()
  await page.getByLabel('Saved dataset').selectOption('hannover-part1-v4')
  const osm = page.getByRole('region', { name: 'Regional OSM display', exact: true })
  const status = osm.getByTestId('osm-status')
  const map = page.getByRole('region', { name: 'Hannover regional map' })
  await expect(status).toHaveAttribute('data-representation', 'aggregate_overview')
  await expect(osm).toContainText('326,334 original objects; 326,311 drawable')
  await page.getByLabel('Street basemap').uncheck()
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'overview-desktop.png') })
  await page.getByRole('button', { name: 'Focus destination', exact: true }).click()
  await expect(status).toHaveAttribute('data-representation', 'detail')
  await map.screenshot({ path: resolve(output, 'mhh-category.png') })
  const categoriesChecked = []
  for (const category of ['Buildings', 'Roads & paths', 'Land use', 'Natural features']) {
    await osm.getByLabel(category, { exact: true }).uncheck()
    await expect(status).not.toContainText('Loading saved OSM')
    await osm.getByLabel(category, { exact: true }).check()
    await expect(status).toHaveAttribute('data-representation', 'detail')
    categoriesChecked.push(category)
  }
  const costsChecked = []
  await osm.getByLabel('OSM color view').selectOption('cost')
  for (const category of ['building', 'highway', 'landuse', 'natural']) {
    await osm.getByLabel('OSM cost category').selectOption(category)
    await expect(status).toHaveAttribute('data-representation', 'detail')
    costsChecked.push(category)
  }
  await osm.getByLabel('OSM cost category').selectOption('building')
  await expect(status).toHaveAttribute('data-representation', 'detail')
  await map.screenshot({ path: resolve(output, 'mhh-building-cost.png') })
  await osm.getByText('Inspect visible objects (first 50)', { exact: true }).click()
  const first = osm.locator('.osm-object-list').last().getByRole('button').first()
  const selectedId = await first.innerText()
  await first.click()
  const detail = osm.getByRole('region', { name: 'Selected OSM object' })
  await expect(detail.getByText('Original tags', { exact: true })).toBeVisible()
  await expect(detail).toContainText('Rule version: ramke-building-tags-v1')
  const routePanel = page.getByRole('region', { name: 'Regional route planning' })
  await routePanel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await routePanel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  await routePanel.getByLabel('Planning mode').selectOption('research')
  await routePanel.getByLabel('Background score assumption').fill('0')
  const beforeRoute = requests.length
  const started = Date.now()
  await routePanel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(routePanel.getByRole('status')).toContainText('Length 3715.6 m')
  const routeWallMs = Date.now() - started
  await expect(detail).toContainText(selectedId)
  expect(requests.length).toBe(beforeRoute)
  const routeOsmRequests = requests.length - beforeRoute
  await expect(map.locator('.leaflet-regional-route-pane svg')).toBeAttached()
  const downloadPromise = page.waitForEvent('download')
  await routePanel.getByRole('button', { name: 'Export displayed result' }).click()
  await (await downloadPromise).saveAs(resolve(output, 'displayed-route.geojson'))
  const exported = JSON.parse(await readFile(resolve(output, 'displayed-route.geojson'), 'utf8'))
  expect(exported.features[0].geometry.coordinates[0]).toEqual([9.7967855, 52.4044919])
  expect(exported.features[0].geometry.coordinates.at(-1)).toEqual([9.8044306, 52.3834796])
  await map.screenshot({ path: resolve(output, 'route-osm-on.png') })
  await osm.getByLabel('Show saved OSM').uncheck()
  await expect(routePanel.getByRole('button', { name: 'Export displayed result' })).toBeVisible()
  await osm.getByLabel('Show saved OSM').check()
  await expect(status).toHaveAttribute('data-representation', 'detail')
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(status).not.toContainText('Loading saved OSM')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'mobile.png') })
  await Promise.all(pending)
  expect(errors).toEqual([])
  expect(datasetRequests.some(url => /\/hannover-part1-v4\/features(?:\?|$)/.test(url))).toBe(false)
  expect(await sha(source)).toBe(originalHash)
  const evidence = { recorded_at: new Date().toISOString(), source_sha256: originalHash, source_unchanged: true,
    categories_checked: categoriesChecked, costs_checked: costsChecked, original_object_checked: selectedId,
    route_length_m: exported.metadata.length_m, route_wall_ms: routeWallMs, route_preserved_selection: true,
    route_caused_osm_requests: routeOsmRequests, mobile_no_horizontal_overflow: true, page_errors: errors,
    requests, responses, limitations: 'Part 3 functional verification; one historical research route with OSM enabled. No Part 4 off/on overhead comparison, 50-cycle resource campaign or browser-memory benchmark.' }
  await writeFile(resolve(output, 'evidence.json'), JSON.stringify(evidence, null, 2))
  console.log(JSON.stringify({ output, page_errors: errors, route_wall_ms: routeWallMs, responses: responses.length, source_unchanged: true }))
} finally { await browser.close() }
