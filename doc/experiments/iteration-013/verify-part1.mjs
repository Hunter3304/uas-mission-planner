// Real retained Hannover data; write evidence only under a new local output.
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { readFile, writeFile } from 'node:fs/promises'
import { createReadStream } from 'node:fs'
import { createHash } from 'node:crypto'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const output = resolve(process.argv[2])
const require = createRequire(resolve(root, 'frontend/package.json'))
const { chromium, expect: baseExpect } = require('@playwright/test')
const expect = baseExpect.configure({ timeout: 180_000 })
async function sha(path) {
  const hash = createHash('sha256')
  for await (const chunk of createReadStream(path)) hash.update(chunk)
  return hash.digest('hex')
}
const studyPath = resolve(root, 'data/hannover-part1-v4/study.json')
const sourcePath = resolve(root, 'data/hannover-part1-v4/osm/features.gpkg')
const before = { study: await sha(studyPath), osm: await sha(sourcePath) }
const study = JSON.parse(await readFile(studyPath, 'utf8'))
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome', headless: true })
const evidence = { recorded_at: new Date().toISOString(), scenario_requests: [], route_requests: [], layer_response_bytes: [], errors: [], passed: false }
evidence.implementation_hashes = Object.fromEntries(await Promise.all(['frontend/src/RegionalMap.tsx', 'frontend/src/RegionalRouting.tsx', 'frontend/src/RegionalOsm.tsx', 'frontend/src/regionalLayers.ts', 'frontend/src/useScenarioLayers.ts', 'frontend/src/RestrictionProfiles.tsx', 'frontend/src/styles.css', 'backend/src/uas_planner/api/app.py'].map(async path => [path, await sha(resolve(root, path))])))
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(180_000)
  const requests = []
  page.on('pageerror', error => evidence.errors.push(error.message))
  page.on('request', request => {
    if (request.url().includes('/api/')) requests.push(request.url())
    if (request.url().endsWith('/study/layers/constraints')) evidence.scenario_requests.push(request.postDataJSON())
    if (request.url().endsWith('/study/route')) evidence.route_requests.push(request.postDataJSON())
  })
  page.on('response', response => {
    if (response.url().endsWith('/study/layers/constraints')) evidence.layer_response_bytes.push({ status: response.status(), bytes: Number(response.headers()['content-length'] ?? 0) })
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.goto(process.env.UAS_UI_URL)
  await page.getByLabel('Saved dataset').selectOption('hannover-part1-v4')
  const panel = page.getByRole('region', { name: 'Regional route planning', exact: true })
  const dipul = page.getByRole('region', { name: 'DIPUL restrictions', exact: true })
  const osm = page.getByRole('region', { name: 'OSM', exact: true })
  const ghsl = page.getByRole('region', { name: 'GHSL population', exact: true })
  const map = page.getByRole('region', { name: 'Hannover regional map', exact: true })
  await expect(panel.getByLabel('Origin', { exact: true }).locator('option')).toHaveCount(8)
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'aggregate_overview')
  console.log('Real OSM overview ready')
  await page.getByLabel('Street basemap').uncheck()
  await expect(page.getByLabel('Original DIPUL')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Load scenario layers', exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Use explicitly selected launch/landing coordinates')).toHaveCount(0)
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  const start = Date.now()
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  console.log('Real conservative scenario ready')
  evidence.initial_scenario_ms = Date.now() - start
  evidence.source_counts = { osm: await page.getByTestId('osm-layer-state').innerText(), dipul: await page.getByTestId('dipul-layer-state').innerText() }
  const requestCount = evidence.scenario_requests.length
  const allRequestsBefore = requests.length
  for (let i = 0; i < 10; i++) {
    await dipul.getByLabel('Policy exclusions').uncheck()
    await dipul.getByLabel('Effective constraints').uncheck()
    await osm.getByLabel('Building obstacles').uncheck()
    await dipul.getByRole('button', { name: 'Collapse DIPUL restrictions' }).click()
    await dipul.getByRole('button', { name: 'Expand DIPUL restrictions' }).click()
    await dipul.getByLabel('Policy exclusions').check()
    await osm.getByLabel('Building obstacles').check()
  }
  await page.waitForTimeout(500)
  expect(evidence.scenario_requests.length).toBe(requestCount)
  expect(requests.length).toBe(allRequestsBefore)
  expect(evidence.route_requests.length).toBe(0)
  evidence.toggle_cycles = 10
  evidence.toggle_requests = requests.length - allRequestsBefore
  console.log('Ten real visibility cycles used no requests')
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).check()
  await expect(ghsl).toContainText('Ready ·')
  const populationBefore = requests.filter(url => url.includes('/study/population')).length
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).uncheck()
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).check()
  await page.waitForTimeout(500)
  expect(requests.filter(url => url.includes('/study/population')).length).toBe(populationBefore)
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).uncheck()
  evidence.population_requests = populationBefore
  console.log('Real GHSL loaded and cached')
  await page.locator('.regional-map-controls').screenshot({ path: resolve(output, 'map-controls-desktop.png') })
  await map.screenshot({ path: resolve(output, 'constraints-map.png') })
  await panel.getByLabel('Selection method').selectOption('coordinates')
  const origin = study.config.locations.find(site => site.id === 'rheuma-podbi')
  const destination = study.config.locations.find(site => site.id === 'mhh')
  for (const [label, value] of [['Start longitude', origin.longitude], ['Start latitude', origin.latitude], ['End longitude', destination.longitude], ['End latitude', destination.latitude]]) await panel.getByLabel(label).fill(String(value))
  await expect(panel.locator('#endpoint-bounds')).toContainText(String(Number(study.config.bounds.west.toFixed(6))))
  await panel.locator('.endpoint-section').screenshot({ path: resolve(output, 'endpoints-desktop.png') })
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await panel.getByLabel('Planning mode', { exact: true }).selectOption('research')
  await panel.getByLabel('Background score assumption').fill('0')
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  console.log('Real research scenario ready')
  const routeStart = Date.now()
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('Length 3715.6 m')
  evidence.route_ms = Date.now() - routeStart
  const downloaded = page.waitForEvent('download')
  await panel.getByRole('button', { name: 'Export displayed result' }).click()
  const exportPath = resolve(output, 'displayed-route.geojson')
  await (await downloaded).saveAs(exportPath)
  const exported = JSON.parse(await readFile(exportPath, 'utf8'))
  expect(exported.features[0].geometry.coordinates[0]).toEqual([origin.longitude, origin.latitude])
  expect(exported.features[0].geometry.coordinates.at(-1)).toEqual([destination.longitude, destination.latitude])
  expect(evidence.route_requests[0].start_coordinate).toEqual([origin.longitude, origin.latitude])
  await panel.getByLabel('Selection method').selectOption('sites')
  await expect(panel.getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
  await page.setViewportSize({ width: 390, height: 844 })
  await panel.getByLabel('Selection method').selectOption('coordinates')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await panel.locator('.endpoint-section').screenshot({ path: resolve(output, 'endpoints-mobile.png') })
  await page.locator('.regional-map-controls').screenshot({ path: resolve(output, 'map-controls-mobile.png') })
  expect(requests.some(url => url.includes('/study/layers/zones'))).toBe(false)
  expect(evidence.errors).toEqual([])
  const after = { study: await sha(studyPath), osm: await sha(sourcePath) }
  expect(after).toEqual(before)
  evidence.source_hashes = { before, after }
  evidence.passed = true
} finally {
  if (!evidence.passed) await browser.contexts()[0]?.pages()[0]?.screenshot({ path: resolve(output, 'failure.png'), fullPage: true }).catch(() => {})
  await writeFile(resolve(output, 'browser-evidence.json'), JSON.stringify(evidence, null, 2))
  await browser.close()
}
console.log(JSON.stringify({ passed: evidence.passed, initial_scenario_ms: evidence.initial_scenario_ms, route_ms: evidence.route_ms, toggle_requests: evidence.toggle_requests, source_counts: evidence.source_counts }))
