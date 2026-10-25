// Isolated real Hannover UI acceptance; original sources are read, never acquired.
import { chromium, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '../../..')
const output = resolve(root, process.argv[2] || '.cache/iteration014-part3-real-v1')
await mkdir(output, { recursive: true })
const hashes = async () => Object.fromEntries(await Promise.all(['study.json', 'population.tif', 'osm/features.gpkg'].map(async name => [name, createHash('sha256').update(await readFile(resolve(root, 'data/hannover-part1-v4', name))).digest('hex')])))
const before = await hashes(), errors = [], services = [], requests = [], results = {}
let browser, populationRequests = 0
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
  for (const url of ['http://127.0.0.1:8016/api/health', 'http://127.0.0.1:5188']) {
    let occupied = false
    try { await fetch(url, { signal: AbortSignal.timeout(1000) }); occupied = true } catch { /* free */ }
    if (occupied) throw new Error(`Acceptance port occupied: ${url}`)
  }
  start(resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python'),
    ['-m', 'uvicorn', 'uas_planner.api.app:create_app', '--factory', '--host', '127.0.0.1', '--port', '8016'],
    { cwd: root, env: { ...process.env, UAS_DATA_DIR: resolve(root, 'data') } })
  start(process.execPath, [resolve(root, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5188'],
    { cwd: resolve(root, 'frontend'), env: { ...process.env, UAS_API_URL: 'http://127.0.0.1:8016' } })
  await Promise.all([ready('http://127.0.0.1:8016/api/health'), ready('http://127.0.0.1:5188')])
  browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    if (request.url().includes('/study/population-costs')) populationRequests++
    if (request.url().endsWith('/study/route')) requests.push(request.postDataJSON())
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.goto('http://127.0.0.1:5188')
  await page.getByLabel('Saved dataset', { exact: true }).selectOption('hannover-part1-v4')
  const panel = page.getByRole('region', { name: 'Regional route planning', exact: true })
  await expect(panel.getByLabel('Origin', { exact: true })).toBeEnabled({ timeout: 120_000 })
  for (const name of ['Street basemap — online OpenStreetMap tiles', 'Show saved OSM', 'Building obstacles — red buffered footprints'])
    await page.getByLabel(name, { exact: true }).uncheck()
  const dipul = page.getByRole('region', { name: 'DIPUL restrictions', exact: true })
  for (const name of ['Effective constraints — red buffered footprints', 'Policy exclusions — orange, unresolved zones'])
    await dipul.getByLabel(name, { exact: true }).uncheck()
  await expect(panel.getByLabel('Include population', { exact: true })).not.toBeChecked()
  await expect(panel.getByLabel('Population weight', { exact: true })).toHaveCount(0)
  await panel.getByLabel('Selection method').selectOption('coordinates')
  for (const [label, value] of [['Start longitude', '9.7967855'], ['Start latitude', '52.4044919'], ['End longitude', '9.8044306'], ['End latitude', '52.3834796']])
    await panel.getByLabel(label + ' (decimal degrees)', { exact: true }).fill(value)
  await panel.getByLabel('Planning mode', { exact: true }).selectOption('research')
  await panel.getByLabel('Background score assumption', { exact: true }).fill('0')
  await panel.getByLabel('Search budget (s)', { exact: true }).fill('20')
  await panel.getByLabel('Include population', { exact: true }).check()
  await panel.getByLabel('Departure time', { exact: true }).fill('2026-10-07T10:00')
  for (const objective of ['risk', 'distance']) {
    await panel.getByLabel('Objective', { exact: true }).selectOption(objective)
    const pending = page.waitForResponse(response => response.url().endsWith('/study/route'), { timeout: 120_000 })
    const started = performance.now()
    await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
    const http = await pending
    if (!http.ok()) throw new Error(`Route API ${http.status()}: ${await http.text()}`)
    const result = await http.json()
    if (result.status !== 'success' || !result.independent_validation || !result.population_active) throw new Error(`Unexpected ${objective} route: ${result.status}: ${result.message}`)
    const costs = panel.getByRole('region', { name: 'Route costs', exact: true })
    await expect(costs).toContainText(`Population cost ${result.population_length_cost.toFixed(2)} score-metres`)
    await expect(costs).toContainText(`Objective cost ${result.objective_cost.toFixed(2)}`)
    await expect(page.getByRole('region', { name: 'Flight time estimate', exact: true })).not.toContainText('Awaiting route')
    if (objective === 'distance') await expect(costs).not.toContainText('Building cost')
    const download = page.waitForEvent('download')
    await panel.getByRole('button', { name: 'Export displayed result', exact: true }).click()
    const artifact = await download
    await artifact.saveAs(resolve(output, `${objective}-displayed.geojson`))
    const data = JSON.parse(await readFile(resolve(output, `${objective}-displayed.geojson`), 'utf8'))
    if (data.metadata.population_model.identity !== result.population_model.identity || data.features[0].properties.population_length_cost !== result.population_length_cost || data.metadata.timing.estimated_arrival !== result.timing.estimated_arrival) throw new Error('Displayed export mismatch')
    const weights = result.effective_weights
    const computed = weights.distance * result.length_m + weights.building * (result.risk_length_cost ?? 0) + weights.population * result.population_length_cost
    if (Math.abs(computed - result.objective_cost) > 1e-6) throw new Error('Combined objective mismatch')
    results[objective] = { status: result.status, browser_solve_ms: performance.now() - started, length_m: result.length_m, building_cost: result.risk_length_cost, population_cost: result.population_length_cost, objective_cost: result.objective_cost, effective_weights: weights, population_identity: result.population_model.identity }
    console.log(JSON.stringify({ objective, ...results[objective] }))
  }
  await panel.screenshot({ path: resolve(output, 'desktop-routing.png') })
  await page.setViewportSize({ width: 390, height: 844 })
  if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw new Error('Mobile horizontal overflow')
  await panel.screenshot({ path: resolve(output, 'mobile-routing.png') })
  await panel.getByLabel('Include population', { exact: true }).uncheck()
  await expect(panel.getByLabel('Population weight', { exact: true })).toHaveCount(0)
  await expect(panel.getByRole('status')).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Flight time estimate', exact: true })).toContainText('Awaiting route')
  if (populationRequests || requests.length !== 2 || requests.some(request => request.population_weight !== 1 || !request.include_population)) throw new Error('Unexpected population display/solve requests')
  if (results.risk.population_identity !== results.distance.population_identity) throw new Error('Population reference changed')
  const after = await hashes()
  if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('Original source hashes changed')
  if (errors.length) throw new Error(errors.join('\n'))
  const acceptance = { passed: true, results, population_display_requests: populationRequests, route_requests: requests.length, source_hashes: after, errors }
  await writeFile(resolve(output, 'acceptance.json'), JSON.stringify(acceptance, null, 2))
  console.log(JSON.stringify({ passed: true, output }))
} finally {
  await browser?.close()
  for (const child of services.reverse()) child.kill()
}
