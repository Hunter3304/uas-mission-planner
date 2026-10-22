// Part 4 real TCP + production-browser acceptance. Invoked by verify-part4.py.
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { readFile, writeFile } from 'node:fs/promises'
import { createReadStream } from 'node:fs'
import { createHash } from 'node:crypto'
import os from 'node:os'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const require = createRequire(resolve(root, 'frontend/package.json'))
const { chromium, expect: baseExpect } = require('@playwright/test')
const expect = baseExpect.configure({ timeout: 180_000 })
const output = resolve(process.argv[2])
const api = process.env.UAS_API_URL ?? 'http://127.0.0.1:8016'
const ui = process.env.UAS_UI_URL ?? 'http://127.0.0.1:5186'
const dataset = 'hannover-part1-v4'
const base = `/api/datasets/${dataset}/study/osm`
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex')
const quantile = (values, q) => [...values].sort((a, b) => a - b)[Math.ceil(values.length * q) - 1]
const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)]
async function sha(path) {
  const hash = createHash('sha256')
  for await (const chunk of createReadStream(path)) hash.update(chunk)
  return hash.digest('hex')
}
const sources = [
  'data/hannover-part1-v4/osm/features.gpkg', 'data/hannover-part1-v4/osm/metadata.json',
  'data/hannover-part1-v4/study.json', 'data/braunschweig-part1-v2/osm/features.gpkg',
  'backend/src/uas_planner/core/cost_rules.json',
]
const hashes = Object.fromEntries(await Promise.all(sources.map(async path => [path, await sha(resolve(root, path))])))
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome', headless: true })
const evidence = {
  recorded_at: new Date().toISOString(), browser: browser.version(), node: process.version,
  hardware: { cpu: os.cpus()[0]?.model, logical_cpus: os.cpus().length, ram_bytes: os.totalmem() },
  mode: 'Production Vite preview, headless installed Chrome, no online tiles; disk cache not flushed',
  viewport: { width: 1440, height: 1000 }, hashes, api_queries: [], views: [], cycles: [],
  responses: [], route_runs: [], errors: [], limitations: [], phase_times: [],
}
const pendingBodies = [], inFlight = new Set()
let osmRequests = 0
let page
function phase(name) { evidence.phase_times.push({ name, utc: new Date().toISOString() }) }
try {
  page = await browser.newPage({ viewport: evidence.viewport })
  page.setDefaultTimeout(180_000)
  page.on('pageerror', error => evidence.errors.push(error.message))
  page.on('request', request => {
    if (request.url().includes('/study/osm/')) { inFlight.add(request); osmRequests++ }
    if (/\/hannover-part1-v4\/features(?:\?|$)/.test(request.url()))
      evidence.errors.push('Legacy unbounded Hannover request')
  })
  page.on('requestfailed', request => inFlight.delete(request))
  page.on('requestfinished', request => inFlight.delete(request))
  function checkBody(data, bytes) {
    if (!data.display || !Array.isArray(data.features)) return
    const detail = data.display.representation === 'detail'
    expect(bytes).toBeLessThanOrEqual(5 * 1024 * 1024)
    expect(data.features.length).toBeLessThanOrEqual(detail ? 5000 : 1600)
    expect(data.display.coordinates ?? 0).toBeLessThanOrEqual(100000)
  }
  page.on('response', response => {
    if (!response.url().includes('/study/osm/') || !response.ok()) return
    pendingBodies.push((async () => {
      try {
        const bytes = await response.body(), data = JSON.parse(bytes.toString())
        checkBody(data, bytes.length)
        evidence.responses.push({ url: response.url(), bytes: bytes.length,
          representation: data.display?.representation ?? data.state,
          count: data.features?.length, coordinates: data.display?.coordinates,
          complete: data.display?.complete, elapsed_ms: response.request().timing().responseEnd })
      } catch (error) {
        // Aborted browser bodies are expected during the explicit rapid-change test.
        if (!/Protocol error|Target closed|No resource|No data|aborted|canceled/i.test(String(error)))
          evidence.errors.push(String(error))
      }
    })())
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Performance.enable')
  async function heap(gc = false) {
    if (gc) await cdp.send('HeapProfiler.collectGarbage')
    const metrics = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m => [m.name, m.value]))
    return { js_heap_used: metrics.JSHeapUsedSize, js_heap_total: metrics.JSHeapTotalSize,
      ...await cdp.send('Memory.getDOMCounters') }
  }
  // Harness-only inspection of the pinned React/Leaflet runtime; no product hooks.
  async function state(action) {
    return page.evaluate(action => {
      const element = document.querySelector('.regional-osm')
      let fiber = element?.[Object.keys(element).find(key => key.startsWith('__reactFiber$'))]
      while (fiber && !(fiber.memoizedProps?.map?.getBounds && fiber.memoizedProps?.datasetId)) fiber = fiber.return
      if (!fiber) throw new Error('Pinned React/Leaflet inspection unavailable')
      const map = fiber.memoizedProps.map
      if (action) { map.setView([action.lat, action.lon], action.zoom, { animate: false }); return }
      let hook = fiber.memoizedState, cache
      while (hook) {
        if (hook.memoizedState?.current instanceof Map) cache = hook.memoizedState.current
        hook = hook.next
      }
      const layers = Object.values(map._layers)
      return { center: map.getCenter(), zoom: map.getZoom(), map_layers: layers.length,
        site_markers: layers.filter(layer => layer._tooltip && layer.options?.radius === 7).length,
        render_layers: Object.keys(map._renderer?._layers ?? {}).length,
        canvases: map.getContainer().querySelectorAll('canvas').length,
        map_handlers: Object.fromEntries(Object.entries(map._events).map(([key, value]) => [key, value.length])),
        cache_entries: cache?.size,
        cache_bytes: cache ? [...cache.values()].reduce((sum, entry) => sum + entry.bytes, 0) : null }
    }, action)
  }
  const osm = page.getByRole('region', { name: 'Regional OSM display', exact: true })
  const status = osm.getByTestId('osm-status')
  async function settled() {
    await expect(status).toContainText(/individual OSM|Aggregate OSM|No matching OSM|Outside saved/)
    await expect(osm.getByRole('alert')).toHaveCount(0)
    await page.waitForFunction(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)))))
    expect(inFlight.size).toBe(0)
  }
  async function apiQuery(path) {
    const t = performance.now()
    const response = await page.request.get(`${api}${path}`)
    expect(response.ok()).toBe(true)
    const body = await response.body(), data = JSON.parse(body.toString())
    checkBody(data, body.length)
    return { data, wall_ms: performance.now() - t, bytes: body.length }
  }
  phase('cold_tcp')
  const coldSummary = await apiQuery(`${base}/summary`)
  evidence.cold_summary = { wall_ms: coldSummary.wall_ms, summary: coldSummary.data }
  const coldDetail = await apiQuery(`${base}/features?bbox=9.800,52.381,9.808,52.386&zoom=16`)
  evidence.cold_detail = { wall_ms: coldDetail.wall_ms, bytes: coldDetail.bytes, display: coldDetail.data.display }
  const regions = [
    ['mhh', 9.8044306, 52.3834796], ['podbi', 9.7967855, 52.4044919],
    ['central', 9.738, 52.373], ['lehrte', 10, 52.375],
    ['boundary', coldSummary.data.coverage_bounds[0] + 0.001, coldSummary.data.coverage_bounds[1] + 0.001],
  ]
  phase('warm_tcp')
  for (const [region, lon, lat] of regions) {
    for (const span of [0.001, 0.002, 0.004, 0.008]) {
      const bbox = [lon - span, lat - span / 2, lon + span, lat + span / 2]
      const r = await apiQuery(`${base}/features?${new URLSearchParams({ bbox: bbox.join(','), zoom: '16' })}`)
      evidence.api_queries.push({ region, bbox, wall_ms: r.wall_ms, bytes: r.bytes, display: r.data.display })
    }
  }
  console.log('Twenty warm TCP queries complete')
  phase('initial_browser')
  await page.goto(ui)
  await expect(page.getByLabel('Saved dataset')).toBeEnabled()
  let t = performance.now()
  await page.getByLabel('Saved dataset').selectOption(dataset)
  await expect(page.getByLabel('Origin', { exact: true })).toBeEnabled()
  await expect.poll(async () => (await state()).site_markers).toBe(8)
  await settled()
  evidence.initial_fit_ms = performance.now() - t
  await expect(status).toHaveAttribute('data-representation', 'aggregate_overview')
  await expect(osm).toContainText('326,334 original objects; 326,311 drawable')
  await page.getByLabel('Street basemap').uncheck()
  evidence.initial_state = await state()
  // Eight site markers are present alongside the 1,580 overview cells.
  expect(evidence.initial_state.site_markers).toBe(8)
  expect(evidence.initial_state.render_layers).toBeGreaterThanOrEqual(1588)
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'overview-desktop.png') })
  await page.getByRole('region', { name: 'Hannover regional map' }).scrollIntoViewIfNeeded()
  phase('browser_views')
  for (const [region, lon, lat] of regions) {
    for (const zoom of [17, 16, 15, 14]) {
      t = performance.now()
      await state({ lon, lat, zoom })
      await settled()
      evidence.views.push({ region, lon, lat, zoom, settled_to_painted_ms: performance.now() - t,
        representation: await status.getAttribute('data-representation'), state: await state(), heap: await heap() })
      console.log(JSON.stringify({ view: evidence.views.at(-1) }))
    }
  }
  await state({ lon: 9.8044306, lat: 52.3834796, zoom: 16 })
  await settled()
  evidence.category_toggles = []
  for (const label of ['Buildings', 'Roads & paths', 'Land use', 'Natural features']) {
    await osm.getByLabel(label, { exact: true }).uncheck()
    await settled()
    await osm.getByLabel(label, { exact: true }).check()
    await settled()
    evidence.category_toggles.push(label)
  }
  evidence.resource_before = { state: await state(), heap: await heap(true) }
  phase('fifty_cycles')
  for (let i = 0; i < 50; i++) {
    const step = i % 10, [region, lon, lat] = regions[step % 5]
    const cost = step % 2 === 1
    await osm.getByLabel('OSM color view').selectOption(cost ? 'cost' : 'category')
    if (cost) await osm.getByLabel('OSM cost category').selectOption(['building', 'highway', 'landuse', 'natural'][Math.floor(step / 2) % 4])
    await state({ lon, lat, zoom: step === 9 ? 14 : 16 })
    await settled()
    const current = await state()
    expect(current.cache_entries).toBeLessThanOrEqual(4)
    expect(current.cache_bytes).toBeLessThanOrEqual(8 * 1024 * 1024)
    evidence.cycles.push({ i: i + 1, region, cost, state: current, active_osm_requests: inFlight.size,
      heap: await heap(), retained_heap: step === 9 ? await heap(true) : undefined })
    if (step === 9) console.log(JSON.stringify({ cycle_checkpoint: evidence.cycles.at(-1) }))
  }
  phase('rapid_and_details')
  const checkpoints = evidence.cycles.filter(c => c.retained_heap)
  expect(new Set(checkpoints.map(c => c.state.map_layers)).size).toBe(1)
  expect(new Set(checkpoints.map(c => c.state.render_layers)).size).toBe(1)
  expect(new Set(checkpoints.map(c => JSON.stringify(c.state.map_handlers))).size).toBe(1)
  // A 20% retained-heap increase over identical checkpoints triggers investigation.
  evidence.retained_heap_growth_ratio = checkpoints.at(-1).retained_heap.js_heap_used / checkpoints[0].retained_heap.js_heap_used - 1
  expect(evidence.retained_heap_growth_ratio).toBeLessThanOrEqual(0.20)
  // Rapid superseding movements/styles settle to the final view, without stale data.
  for (let i = 0; i < 12; i++) await state({ lon: regions[i % 5][1], lat: regions[i % 5][2], zoom: i % 2 ? 16 : 14 })
  await osm.getByLabel('OSM color view').selectOption('category')
  await state({ lon: 9.8044306, lat: 52.3834796, zoom: 16 })
  await settled()
  await expect(status).toHaveAttribute('data-representation', 'detail')
  evidence.rapid_final_state = await state()
  await osm.getByText('Inspect visible objects (first 50)', { exact: true }).click()
  const first = osm.locator('.osm-object-list').last().getByRole('button').first()
  evidence.selected_object = await first.innerText()
  await first.click()
  await expect(osm.getByRole('region', { name: 'Selected OSM object' })).toContainText('Original tags')
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'mhh-details-desktop.png') })
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  await panel.getByLabel('Planning mode').selectOption('research')
  await panel.getByLabel('Background score assumption').fill('0')
  let reference, requestPayload
  async function routeRun(enabled, measured) {
    await osm.getByLabel('Show saved OSM').setChecked(enabled)
    if (enabled) await settled()
    else await expect(status).toContainText('OSM display is off')
    const count = osmRequests, before = await state()
    const responsePromise = page.waitForResponse(r => r.url().endsWith('/study/route') && r.request().method() === 'POST')
    const start = performance.now()
    await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
    const response = await responsePromise
    const result = await response.json()
    await expect(panel.getByRole('status')).toContainText('success')
    await expect(panel).toContainText('Length 3715.6 m')
    const wall_ms = performance.now() - start
    expect(result.status).toBe('success')
    const meaning = { geometry: result.geometry, length_m: result.length_m,
      risk_length_cost: result.risk_length_cost, objective_cost: result.objective_cost,
      endpoint_diagnostics: result.endpoint_diagnostics, research_assumptions: result.research_assumptions,
      restriction_report: result.restriction_report, mission: result.mission }
    if (!reference) { reference = meaning; requestPayload = response.request().postDataJSON() }
    expect(meaning).toEqual(reference)
    expect(response.request().postDataJSON()).toEqual(requestPayload)
    expect(osmRequests - count).toBe(0)
    expect((await state()).center).toEqual(before.center)
    const row = { enabled, measured, wall_ms, preparation_ms: result.preparation_ms,
      source_preparation_ms: result.source_preparation_ms, planner_ms: result.planner_ms,
      runtime_ms: result.runtime_ms, meaning_sha256: digest(meaning), osm_requests: osmRequests - count }
    evidence.route_runs.push(row)
    console.log(JSON.stringify({ route: row }))
    const downloadPromise = page.waitForEvent('download')
    await panel.getByRole('button', { name: 'Export displayed result' }).click()
    const file = resolve(output, `route-${evidence.route_runs.length}-${enabled ? 'on' : 'off'}.geojson`)
    await (await downloadPromise).saveAs(file)
    const exported = JSON.parse(await readFile(file, 'utf8'))
    expect(exported.features[0].geometry).toEqual(result.geometry)
    expect(exported.features[0].geometry.coordinates[0]).toEqual([9.7967855, 52.4044919])
    expect(exported.features[0].geometry.coordinates.at(-1)).toEqual([9.8044306, 52.3834796])
    return result
  }
  // Both states warm up; alternate measured order to avoid cold-preparation bias.
  phase('route_comparison')
  await routeRun(false, false)
  await routeRun(true, false)
  for (const enabled of [false, true, true, false, false, true]) await routeRun(enabled, true)
  evidence.route_request = requestPayload
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'route-osm-on.png') })
  phase('conservative_rejection')
  const conservative = await page.request.post(`${api}/api/datasets/${dataset}/study/route`, {
    data: { ...requestPayload, planning_mode: 'conservative' }, timeout: 180000,
  })
  expect(conservative.ok()).toBe(true)
  const rejection = await conservative.json()
  expect(rejection.status).toBe('invalid_endpoint')
  expect(rejection.geometry).toBeNull()
  evidence.conservative = rejection
  phase('mobile_and_braunschweig')
  await page.setViewportSize({ width: 390, height: 844 })
  await settled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'hannover-mobile.png') })
  await page.getByLabel('Saved dataset').selectOption('braunschweig-part1-v2')
  await expect(page.getByTestId('total-count')).toHaveText('31,496')
  await expect(page.getByTestId('cost-summary')).toBeVisible()
  for (const category of ['building', 'highway', 'landuse', 'natural']) {
    await page.getByLabel('Cost category', { exact: true }).selectOption(category)
    await expect(page.getByTestId('cost-summary')).toBeVisible()
  }
  await expect(page.getByRole('region', { name: 'External layers', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Inspect start', exact: true }).click()
  await expect(page.getByTestId('external-location')).toContainText('Terrain elevation:')
  await expect(page.getByTestId('external-location')).toContainText('Population:')
  await page.getByLabel('DIPUL zones', { exact: true }).check()
  await page.getByLabel('GHSL population', { exact: false }).uncheck()
  await page.getByRole('button', { name: 'Inspect end', exact: true }).click()
  await expect(page.getByTestId('external-location')).toContainText('Aircraft altitude:')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: resolve(output, 'braunschweig-mobile.png') })
  await page.setViewportSize(evidence.viewport)
  await page.screenshot({ path: resolve(output, 'braunschweig-desktop.png') })
  evidence.braunschweig = { original_count: 31496, categories: ['building', 'highway', 'landuse', 'natural'], mobile_no_overflow: true }
  await Promise.all(pendingBodies)
  expect(evidence.errors).toEqual([])
  for (const [path, hash] of Object.entries(hashes)) expect(await sha(resolve(root, path))).toBe(hash)
  evidence.sources_unchanged = true
  const off = evidence.route_runs.filter(r => r.measured && !r.enabled).map(r => r.wall_ms)
  const on = evidence.route_runs.filter(r => r.measured && r.enabled).map(r => r.wall_ms)
  evidence.gates = {
    warm_api_p95_ms: quantile(evidence.api_queries.map(r => r.wall_ms), 0.95),
    browser_view_p95_ms: quantile(evidence.views.map(r => r.settled_to_painted_ms), 0.95),
    route_off_median_ms: median(off), route_on_median_ms: median(on),
    route_median_overhead_ratio: median(on) / median(off) - 1,
    fifty_cycles: evidence.cycles.length === 50, sources_unchanged: true,
    browser_heap_peak_sampled: Math.max(...evidence.cycles.map(c => c.heap.js_heap_used)),
  }
  expect(evidence.gates.warm_api_p95_ms).toBeLessThanOrEqual(2000)
  expect(evidence.gates.browser_view_p95_ms).toBeLessThanOrEqual(3000)
  expect(evidence.gates.route_median_overhead_ratio).toBeLessThanOrEqual(0.20)
  evidence.passed = true
  phase('complete')
  console.log(JSON.stringify(evidence.gates, null, 2))
} catch (error) {
  evidence.failure = String(error)
  if (page) await page.screenshot({ path: resolve(output, 'failure.png'), fullPage: true }).catch(() => {})
  throw error
} finally {
  evidence.recorded_until = new Date().toISOString()
  await writeFile(resolve(output, 'browser-evidence.json'), JSON.stringify(evidence, null, 2))
  await browser.close()
}
