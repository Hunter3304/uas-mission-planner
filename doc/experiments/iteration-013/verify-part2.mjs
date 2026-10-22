// Real retained Hannover selection acceptance against isolated production services.
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
const sourcePath = resolve(root, 'data/hannover-part1-v4/osm/features.gpkg')
const studyPath = resolve(root, 'data/hannover-part1-v4/study.json')
const before = { osm: await sha(sourcePath), study: await sha(studyPath) }
const evidence = { recorded_at: new Date().toISOString(), errors: [], source_requests: [], detail_requests: [], scenario_requests: 0, population_requests: 0, route_requests: 0, passed: false }
evidence.implementation_hashes = Object.fromEntries(await Promise.all(['frontend/src/App.tsx', 'frontend/src/RegionalMap.tsx', 'frontend/src/RegionalOsm.tsx', 'frontend/src/RegionalSelection.tsx', 'frontend/src/OsmObjectDetails.tsx', 'frontend/src/mapSelection.ts', 'frontend/src/styles.css'].map(async path => [path, await sha(resolve(root, path))])))
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(180_000)
  page.on('pageerror', error => evidence.errors.push(error.message))
  page.on('request', request => {
    const url = request.url()
    if (/\/study\/osm\/(summary|features\?|overview)/.test(url)) evidence.source_requests.push(url)
    if (/\/study\/osm\/features\//.test(url)) evidence.detail_requests.push(url)
    if (url.endsWith('/study/layers/constraints')) evidence.scenario_requests++
    if (url.includes('/study/population')) evidence.population_requests++
    if (url.endsWith('/study/route')) evidence.route_requests++
  })
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.goto(process.env.UAS_UI_URL)
  await page.getByLabel('Saved dataset').selectOption('hannover-part1-v4')
  const inspector = page.getByRole('region', { name: 'Map object inspector', exact: true })
  const osm = page.getByRole('region', { name: 'Regional OSM display', exact: true })
  const map = page.getByRole('region', { name: 'Hannover regional map', exact: true })
  const black = map.locator('.leaflet-regional-selection-pane path[stroke="#000000"]')
  const routing = page.getByRole('region', { name: 'Regional route planning', exact: true })
  const dipul = page.getByRole('region', { name: 'DIPUL restrictions', exact: true })
  const ghsl = page.getByRole('region', { name: 'GHSL population', exact: true })
  async function centerClick() {
    const box = await map.boundingBox()
    await map.click({ position: { x: box.width / 2, y: box.height / 2 } })
  }
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'aggregate_overview')
  await page.getByLabel('Street basemap').uncheck()
  await page.getByLabel('Locations —').uncheck()
  const overviewBox = await map.boundingBox()
  for (const [x, y] of [[.5, .5], [.4, .5], [.6, .5]]) {
    await map.click({ position: { x: overviewBox.width * x, y: overviewBox.height * y } })
    if ((await inspector.innerText()).includes('Aggregate overview cell')) break
  }
  await expect(inspector).toContainText('Aggregate overview cell')
  await expect(black).toHaveCount(1)
  await inspector.getByRole('button', { name: 'Zoom for objects', exact: true }).click()
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  // Preserve the existing query budget. If it falls back to overview under
  // resource contention, inspect a smaller viewport by zooming in, like a user.
  let fallbackZooms = 0
  await expect.poll(async () => {
    if (await page.getByTestId('osm-status').getAttribute('data-representation') === 'detail') return true
    if (fallbackZooms < 2 && await osm.getByText(/Individual-object display exceeded its limit/).isVisible()) {
      fallbackZooms++
      await map.getByRole('button', { name: 'Zoom in', exact: true }).click()
    }
    return false
  }, { intervals: [1000, 2000, 3000] }).toBe(true)
  evidence.bounded_fallback_zooms = fallbackZooms
  await expect(page.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await osm.getByText('Inspect visible objects (first 50)', { exact: true }).click()
  const items = osm.locator('.osm-object-list').last().getByRole('button')
  const selectedId = await items.first().innerText()
  const mapYBefore = await map.evaluate(element => element.getBoundingClientRect().top + scrollY)
  await items.first().click()
  await expect(inspector.getByRole('region', { name: 'Selected OSM object' })).toContainText(`OSM ${selectedId}`)
  await expect(inspector).toContainText('Original tags')
  await expect(black).toHaveCount(1)
  const leftBox = await inspector.boundingBox(), mapBox = await map.boundingBox()
  expect(leftBox.x + leftBox.width).toBeLessThan(mapBox.x)
  expect(await map.evaluate(element => element.getBoundingClientRect().top + scrollY)).toBe(mapYBefore)
  evidence.osm_selection = selectedId
  evidence.map_vertical_shift_px = 0
  const sourceCount = evidence.source_requests.length
  const detailsCount = evidence.detail_requests.length
  await map.scrollIntoViewIfNeeded()
  await page.getByRole('button', { name: 'View details', exact: true }).click()
  await expect(inspector).toBeFocused()
  await page.screenshot({ path: resolve(output, 'osm-desktop.png') })
  await page.getByRole('button', { name: 'Collapse OSM', exact: true }).click()
  await expect(black).toHaveCount(1)
  await page.getByRole('button', { name: 'Expand OSM', exact: true }).click()
  expect(evidence.source_requests.length).toBe(sourceCount)
  expect(evidence.detail_requests.length).toBe(detailsCount)
  await inspector.getByRole('button', { name: 'Clear selection', exact: true }).click()
  for (let i = 0; i < 10; i++) {
    await items.nth(i % Math.min(2, await items.count())).click()
    await expect(black).toHaveCount(1)
    await expect(map.locator('.leaflet-regional-selection-pane svg')).toHaveCount(1)
    await expect(map.locator('.selection-summary')).toHaveCount(1)
  }
  evidence.selection_cycles = 10
  await expect(inspector.getByRole('region', { name: 'Selected OSM object' })).toContainText('Original tags')
  await osm.getByText('Source geometry diagnostics', { exact: true }).click()
  const diagnostic = osm.locator('.osm-object-list').first().getByRole('button').first()
  evidence.geometry_diagnostic = await diagnostic.innerText()
  await diagnostic.click()
  await expect(inspector).toContainText('No drawable geometry')
  await expect(inspector).toContainText('Drawable: false')
  await expect(inspector).toContainText('Original tags')
  await expect(black).toHaveCount(0)
  await osm.getByLabel('Show saved OSM').uncheck()
  await expect(black).toHaveCount(0)
  await routing.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await routing.getByLabel('Scenario end').fill('2026-10-07T10:15')
  const scenarioStart = Date.now()
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  evidence.scenario_load_ms = Date.now() - scenarioStart
  await centerClick()
  await expect(inspector).toContainText('Selected · DIPUL')
  await expect(black).toHaveCount(1)
  await map.scrollIntoViewIfNeeded()
  await page.screenshot({ path: resolve(output, 'dipul-desktop.png') })
  await dipul.getByLabel('Policy exclusions').uncheck()
  await dipul.getByLabel('Effective constraints').uncheck()
  await page.getByRole('region', { name: 'OSM', exact: true }).getByLabel('Building obstacles').uncheck()
  await expect(black).toHaveCount(0)
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).check()
  await expect(ghsl).toContainText('Ready ·')
  await centerClick()
  await expect(inspector).toContainText('Selected · GHSL')
  await expect(black).toHaveCount(1)
  await map.scrollIntoViewIfNeeded()
  await page.screenshot({ path: resolve(output, 'ghsl-desktop.png') })
  const populationCount = evidence.population_requests
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).uncheck()
  await expect(black).toHaveCount(0)
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).check()
  await centerClick()
  await expect(inspector).toContainText('Selected · GHSL')
  expect(evidence.population_requests).toBe(populationCount)
  await page.setViewportSize({ width: 390, height: 844 })
  await map.scrollIntoViewIfNeeded()
  await expect(inspector).toBeVisible()
  expect((await inspector.boundingBox()).height).toBeLessThanOrEqual(844 * .55 + 1)
  expect(await inspector.evaluate(element => getComputedStyle(element).position)).toBe('fixed')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: resolve(output, 'ghsl-mobile.png') })
  await inspector.getByRole('button', { name: 'Collapse object details', exact: true }).click()
  await page.screenshot({ path: resolve(output, 'collapsed-mobile.png') })
  await inspector.getByRole('button', { name: 'Clear selection', exact: true }).click()
  await expect(black).toHaveCount(0)
  expect(evidence.route_requests).toBe(0)
  expect(evidence.scenario_requests).toBe(1)
  expect(evidence.errors).toEqual([])
  const after = { osm: await sha(sourcePath), study: await sha(studyPath) }
  expect(after).toEqual(before)
  evidence.source_hashes = { before, after }
  evidence.passed = true
} finally {
  if (!evidence.passed) await browser.contexts()[0]?.pages()[0]?.screenshot({ path: resolve(output, 'failure.png'), fullPage: true }).catch(() => {})
  await writeFile(resolve(output, 'browser-evidence.json'), JSON.stringify(evidence, null, 2))
  await browser.close()
}
console.log(JSON.stringify({ passed: evidence.passed, selection_cycles: evidence.selection_cycles, scenario_load_ms: evidence.scenario_load_ms, scenario_requests: evidence.scenario_requests, population_requests: evidence.population_requests }))
