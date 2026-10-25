// Real population display/rendering and retained renderer JS heap; no route solve.
import { chromium, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '../../..')
const output = process.argv[2] ? resolve(process.argv[2]) : resolve(root, '.cache/iteration014-part4-display-v1')
await mkdir(output, { recursive: true })
const hashes = async () => Object.fromEntries(await Promise.all(['study.json', 'population.tif', 'osm/features.gpkg'].map(async name => [name, createHash('sha256').update(await readFile(resolve(root, 'data/hannover-part1-v4', name))).digest('hex')])))
const before = await hashes(), services = [], errors = []
let browser, populationRequests = 0, routeRequests = 0
function start(command, args, options) {
  const child = spawn(command, args, { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'], ...options })
  let stderr = ''
  child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-4000) })
  child.on('error', error => errors.push(error.message))
  child.on('exit', code => { if (code) errors.push(`Service exited ${code}: ${stderr}`) })
  services.push(child)
}
async function ready(url) {
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    try { if ((await fetch(url)).ok) return } catch { /* startup */ }
    if (errors.length) throw new Error(errors.join('\n'))
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`Service not ready: ${url}`)
}
try {
  for (const url of ['http://127.0.0.1:8020/api/health', 'http://127.0.0.1:5190']) {
    let occupied = false
    try { await fetch(url, { signal: AbortSignal.timeout(1000) }); occupied = true } catch { /* free */ }
    if (occupied) throw new Error(`Acceptance port occupied: ${url}`)
  }
  start(resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python'),
    ['-m', 'uvicorn', 'uas_planner.api.app:create_app', '--factory', '--host', '127.0.0.1', '--port', '8020'],
    { cwd: root, env: { ...process.env, UAS_DATA_DIR: resolve(root, 'data') } })
  start(process.execPath, [resolve(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5190'],
    { cwd: resolve(root, 'frontend'), env: { ...process.env, UAS_API_URL: 'http://127.0.0.1:8020' } })
  await Promise.all([ready('http://127.0.0.1:8020/api/health'), ready('http://127.0.0.1:5190')])
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Performance.enable')
  const heap = async () => {
    await cdp.send('HeapProfiler.collectGarbage')
    const { metrics } = await cdp.send('Performance.getMetrics')
    return Object.fromEntries(metrics.filter(m => ['JSHeapUsedSize', 'JSHeapTotalSize', 'Nodes', 'Documents', 'JSEventListeners'].includes(m.name)).map(m => [m.name, m.value]))
  }
  const paint = async () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    if (request.url().includes('/study/population-costs')) populationRequests++
    if (request.url().endsWith('/study/route')) routeRequests++
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.goto('http://127.0.0.1:5190')
  await page.getByLabel('Saved dataset', { exact: true }).selectOption('hannover-part1-v4')
  const panel = page.getByRole('region', { name: 'Regional route planning', exact: true })
  await expect(panel.getByLabel('Origin', { exact: true })).toBeEnabled({ timeout: 120_000 })
  await page.getByLabel('Street basemap — online OpenStreetMap tiles', { exact: true }).uncheck()
  await page.getByLabel('Show saved OSM', { exact: true }).uncheck()
  await page.getByRole('button', { name: 'Collapse Regional route planning', exact: true }).click()
  const initialHeap = await heap()
  const display = page.getByLabel('GHSL — population risk (250 m)', { exact: true })
  const response = page.waitForResponse(response => response.url().includes('/study/population-costs'), { timeout: 120_000 })
  const started = performance.now()
  await display.check()
  const http = await response
  if (!http.ok()) throw new Error(`Display API ${http.status()}`)
  const payload = await http.body(), data = JSON.parse(payload.toString())
  await expect(page.getByTestId('population-cost-state')).toContainText('Ready · 6,759 cells', { timeout: 120_000 })
  await paint()
  const firstVisibleMs = performance.now() - started
  const firstHeap = await heap()
  const cycles = []
  for (let i = 0; i < 10; i++) {
    const started = performance.now()
    await display.uncheck()
    await display.check()
    await paint()
    cycles.push(performance.now() - started)
  }
  const repeatedHeap = await heap()
  if (!data.display.complete || payload.length >= 5 * 1024 * 1024 || populationRequests !== 1 || routeRequests !== 0) throw new Error('Display bounds/cache contract failed')
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'desktop-population.png') })
  const map = page.getByRole('region', { name: 'Hannover regional map', exact: true })
  const bounds = await map.boundingBox()
  await map.click({ position: { x: bounds.width / 2, y: bounds.height / 2 } })
  await expect(page.getByRole('region', { name: 'Map object inspector' })).toContainText('250 m population risk')
  await page.setViewportSize({ width: 390, height: 844 })
  if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw new Error('Mobile horizontal overflow')
  await page.locator('#regional-map').screenshot({ path: resolve(output, 'mobile-population.png') })
  if (JSON.stringify(before) !== JSON.stringify(await hashes())) throw new Error('Source hashes changed')
  if (errors.length) throw new Error(errors.join('\n'))
  const result = { passed: true, first_visible_ms: firstVisibleMs, cached_toggle_cycle_ms: cycles,
    response_bytes: payload.length, cells: data.cell_count, class_counts: data.class_counts,
    identity: data.identity, renderer_metrics: { initial: initialHeap, first_population: firstHeap, after_ten_cycles: repeatedHeap },
    memory_scope: 'Chrome renderer JS heap after explicit GC, DOM nodes/listeners. Excludes browser/native/canvas/GPU allocations; no total-browser-memory or leak-proof claim.',
    population_requests: populationRequests, route_requests: routeRequests, source_hashes: before, errors }
  await writeFile(resolve(output, 'acceptance.json'), JSON.stringify(result, null, 2))
  console.log(JSON.stringify(result))
} finally {
  await browser?.close()
  for (const child of services.reverse()) child.kill()
}
