// Local, isolated Hannover acceptance. Requires installed Python/Node dependencies.
import { chromium, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '../../..')
const output = resolve(root, '.cache/iteration014-real')
await mkdir(output, { recursive: true })
const hashes = async () => Object.fromEntries(await Promise.all(['study.json', 'population.tif'].map(async name => [name, createHash('sha256').update(await readFile(resolve(root, 'data/hannover-part1-v4', name))).digest('hex')])))
const before = await hashes()
const errors = [], services = []
let browser
const start = (command, args, options) => {
  const child = spawn(command, args, { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'], ...options })
  let lastError = ''
  child.stderr.on('data', chunk => { lastError = (lastError + chunk.toString()).slice(-4000) })
  child.on('error', error => errors.push(error.message))
  child.on('exit', code => { if (code) errors.push(`Service exited ${code}: ${lastError}`) })
  services.push(child)
}
async function ready(url) {
  const deadline = Date.now() + 60000
  while (Date.now() < deadline) {
    try { if ((await fetch(url)).ok) return } catch { /* startup */ }
    if (errors.length) throw new Error(errors.join('\n'))
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`Local service did not become ready: ${url}`)
}
try {
  // Verify ports are free before launching; do not attach to or stop user services.
  for (const url of ['http://127.0.0.1:8014/api/health', 'http://127.0.0.1:5186']) {
    let occupied = false
    try { await fetch(url, { signal: AbortSignal.timeout(1000) }); occupied = true } catch { /* free */ }
    if (occupied) throw new Error(`Acceptance port already occupied: ${url}`)
  }
  start(resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python'),
    ['-m', 'uvicorn', 'uas_planner.api.app:create_app', '--factory', '--host', '127.0.0.1', '--port', '8014'],
    { cwd: root, env: { ...process.env, UAS_DATA_DIR: resolve(root, 'data') } })
  start(process.execPath, [resolve(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5186'],
    { cwd: resolve(root, 'frontend'), env: { ...process.env, UAS_API_URL: 'http://127.0.0.1:8014' } })
  await Promise.all([ready('http://127.0.0.1:8014/api/health'), ready('http://127.0.0.1:5186')])
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.on('pageerror', error => errors.push(error.message))
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  let populationRequests = 0, routeRequests = 0
  page.on('request', request => {
    if (request.url().includes('/study/population-costs')) populationRequests++
    if (request.url().endsWith('/study/route')) routeRequests++
  })
  await page.goto('http://127.0.0.1:5186')
  await page.getByLabel('Saved dataset', { exact: true }).selectOption('hannover-part1-v4')
  const ghsl = page.getByRole('region', { name: 'GHSL population', exact: true })
  await expect(ghsl).toBeVisible({ timeout: 120000 })
  await page.getByLabel('Street basemap — online OpenStreetMap tiles', { exact: true }).uncheck()
  await page.getByLabel('Show saved OSM', { exact: true }).uncheck()
  const responsePromise = page.waitForResponse(response => response.url().includes('/study/population-costs'), { timeout: 120000 })
  const started = performance.now()
  await page.getByLabel('GHSL — population risk (250 m)', { exact: true }).check()
  const response = await responsePromise
  if (!response.ok()) throw new Error(`Population API failed: ${response.status()}`)
  const data = await response.json()
  await expect(page.getByTestId('population-cost-state')).toContainText('Ready · 6,759 cells', { timeout: 120000 })
  const elapsed = performance.now() - started
  if (!data.display.complete || data.layer.features.length !== data.cell_count || !data.identity) throw new Error('Incomplete real population display')
  if (data.unknown_cells || Object.values(data.class_counts).some(v => v === 0)) throw new Error('Unexpected Hannover class/support distribution')
  await expect(page.getByLabel('GHSL — population cells', { exact: true })).toHaveCount(0)
  for (let i = 0; i < 10; i++) {
    await page.getByLabel('GHSL — population risk (250 m)', { exact: true }).uncheck()
    await page.getByLabel('GHSL — population risk (250 m)', { exact: true }).check()
  }
  if (populationRequests !== 1 || routeRequests !== 0) throw new Error('Visibility requested repeated preparation or routing')
  await page.getByRole('button', { name: 'Collapse Regional route planning', exact: true }).click()
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'hannover-population-desktop.png') })
  const map = page.getByRole('region', { name: 'Hannover regional map', exact: true })
  const dimensions = await map.boundingBox()
  await map.click({ position: { x: dimensions.width / 2, y: dimensions.height / 2 } })
  await expect(page.getByRole('region', { name: 'Map object inspector' })).toContainText('250 m population risk')
  await page.setViewportSize({ width: 390, height: 844 })
  if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw new Error('Mobile horizontal overflow')
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'hannover-population-mobile.png') })
  const after = await hashes()
  if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('Original population inputs changed')
  if (errors.length) throw new Error(errors.join('\n'))
  const result = { population_requests: populationRequests, route_requests: routeRequests, first_load_ms: elapsed,
    response_bytes: Buffer.byteLength(JSON.stringify(data)), class_counts: data.class_counts,
    cells: data.cell_count, maximum_people_per_km2: data.maximum_people_per_km2,
    identity: data.identity, source_hashes: after, errors, passed: true }
  await writeFile(resolve(output, 'acceptance.json'), JSON.stringify(result, null, 2))
  console.log(JSON.stringify(result))
} finally {
  await browser?.close()
  for (const child of services.reverse()) child.kill()
}
