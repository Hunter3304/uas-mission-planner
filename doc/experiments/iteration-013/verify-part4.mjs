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
evidence.implementation_hashes = Object.fromEntries(await Promise.all(['frontend/src/App.tsx', 'frontend/src/RegionalMap.tsx', 'frontend/src/RegionalOsm.tsx', 'frontend/src/RegionalSelection.tsx', 'frontend/src/OsmObjectDetails.tsx', 'frontend/src/mapSelection.ts', 'frontend/src/styles.css', 'frontend/src/RegionalSourceDetails.tsx', 'frontend/src/RegionalOsmCosts.tsx', 'frontend/src/SourceFacts.tsx', 'frontend/src/sourcePresentation.ts', 'frontend/src/RegionalRouting.tsx', 'frontend/src/RestrictionProfiles.tsx', 'frontend/src/scenarioTime.ts', 'frontend/src/useScenarioLayers.ts', 'frontend/src/api.ts', 'backend/src/uas_planner/core/flight_interval.py', 'backend/src/uas_planner/core/regional_routing.py', 'backend/src/uas_planner/core/regional.py', 'backend/src/uas_planner/core/routing.py', 'backend/src/uas_planner/api/app.py'].map(async path => [path, await sha(resolve(root, path))])))
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(180_000)
  page.on('pageerror', error => evidence.errors.push(error.message))
  page.on('request', request => {
    const url = request.url()
    if (/\/study\/osm\/(summary|features\?|overview)/.test(url)) evidence.source_requests.push(url)
    if (/\/study\/osm\/features\//.test(url)) evidence.detail_requests.push(url)
    if (url.endsWith('/study/layers/constraints')) { evidence.scenario_requests++; (evidence.scenario_bodies ??= []).push(request.postDataJSON()) }
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
  await expect(routing.getByLabel('Scenario end')).toHaveCount(0)
  await expect(page.getByLabel('Original DIPUL')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Load scenario layers', exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Use explicitly selected launch/landing coordinates')).toHaveCount(0)
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
  await expect(inspector.getByRole('region', { name: 'Original source facts' })).toBeVisible()
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
  const popupBounds = await map.locator('.selection-summary').boundingBox()
  const visibleMapBounds = await map.boundingBox()
  expect(popupBounds.x).toBeGreaterThanOrEqual(visibleMapBounds.x)
  expect(popupBounds.x + popupBounds.width).toBeLessThanOrEqual(visibleMapBounds.x + visibleMapBounds.width)
  await expect(inspector.locator('.source-raw pre')).not.toBeVisible()
  await page.screenshot({ path: resolve(output, 'osm-desktop.png') })
  await inspector.getByText('Matched rules and evidence', { exact: true }).first().click()
  await expect(inspector).toContainText('Rule version:')
  await inspector.getByText('Matched rules and evidence', { exact: true }).first().click()
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
  async function waitForObjectCosts() {
    let extraZooms = 0
    await expect.poll(async () => {
      if (await osm.getByTestId('osm-status').getAttribute('data-representation') === 'detail' && (await osm.getByTestId('osm-status').innerText()).includes('individual OSM objects')) return true
      if (extraZooms < 2 && await osm.getByText(/Individual-object display exceeded its limit/).isVisible()) {
        extraZooms++
        await map.getByRole('button', { name: 'Zoom in', exact: true }).click()
      }
      return false
    }, { intervals: [500, 1000, 2000] }).toBe(true)
  }
  const buildingCosts = page.waitForResponse(response => /\/study\/osm\/features\?.*style=cost.*cost_category=building/.test(response.url()))
  await osm.getByLabel('OSM color view').selectOption('cost')
  await buildingCosts
  await waitForObjectCosts()
  await expect(osm).toContainText('not an overall risk surface')
  await expect(osm.getByLabel('OSM legend')).toContainText('4 · Very high')
  const naturalCosts = page.waitForResponse(response => /\/study\/osm\/features\?.*style=cost.*cost_category=natural/.test(response.url()))
  await osm.getByLabel('OSM cost category').selectOption('natural')
  await naturalCosts
  await waitForObjectCosts()
  await osm.getByLabel('OSM color view').selectOption('category')
  await expect(osm.getByTestId('osm-status')).toHaveAttribute('data-representation', 'detail')
  await expect(osm).toContainText('first enabled category')
  evidence.color_modes_verified = true
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
  await routing.getByLabel('Departure time').fill('2026-10-07T10:00')
  const scenarioStart = Date.now()
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  evidence.scenario_load_ms = Date.now() - scenarioStart
  evidence.provisional_end = await page.getByTestId('flight-interval-scope').getAttribute('data-assessed-end')
  await expect(page.getByTestId('flight-interval-scope')).toContainText('Provisional preview')
  await expect(routing.getByRole('region', { name: 'Flight time estimate' })).toContainText('Awaiting route')
  await centerClick()
  await expect(inspector).toContainText('Selected · DIPUL')
  await expect(inspector.getByRole('region', { name: 'Scenario assessment' })).toContainText('Policy exclusion · unresolved')
  await expect(inspector.getByRole('region', { name: 'Scenario assessment' })).toContainText('m AGL')
  await expect(inspector.getByRole('region', { name: 'Source record' })).toContainText('Not supplied')
  await expect(inspector.locator('.source-raw pre')).not.toBeVisible()
  await expect(black).toHaveCount(1)
  await map.scrollIntoViewIfNeeded()
  expect((await inspector.boundingBox()).y).toBeGreaterThanOrEqual(0)
  await page.screenshot({ path: resolve(output, 'dipul-desktop.png') })
  const initialLoads = evidence.scenario_requests
  for (let cycle = 0; cycle < 10; cycle++) {
    await dipul.getByLabel('Policy exclusions').uncheck()
    await dipul.getByLabel('Policy exclusions').check()
  }
  expect(evidence.scenario_requests).toBe(initialLoads)
  evidence.initial_visibility_cycles = 10
  await dipul.getByLabel('Policy exclusions').uncheck()
  await dipul.getByLabel('Effective constraints').uncheck()
  await page.getByRole('region', { name: 'OSM', exact: true }).getByLabel('Building obstacles').uncheck()
  await expect(black).toHaveCount(0)
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).check()
  await expect(ghsl).toContainText('Ready ·')
  await centerClick()
  await expect(inspector).toContainText('Selected · GHSL')
  await expect(inspector.getByRole('region', { name: 'Population estimate' })).toContainText('Estimated population:')
  await expect(inspector.getByRole('region', { name: 'Population estimate' })).toContainText('100 m × 100 m')
  await expect(inspector.getByRole('region', { name: 'Population estimate' })).toContainText('2020')
  await expect(inspector.locator('.source-raw pre')).not.toBeVisible()
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
  evidence.readable_cards = true
  await page.setViewportSize({ width: 1440, height: 1000 })
  await ghsl.getByLabel('GHSL — population cells', { exact: true }).uncheck()
  const failedResponse = page.waitForResponse(response => response.url().endsWith('/study/route'))
  let clock = Date.now()
  await routing.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  const failed = await (await failedResponse).json()
  evidence.conservative_route_ms = Date.now() - clock
  expect(failed.status).not.toBe('success')
  expect(failed.timing.estimated_arrival).toBeNull()
  await expect(routing.getByRole('region', { name: 'Flight time estimate' })).toContainText('Awaiting route')
  evidence.conservative_status = failed.status
  const study = JSON.parse(await readFile(studyPath, 'utf8'))
  const origin = study.config.locations.find(site => site.id === 'rheuma-podbi')
  const destination = study.config.locations.find(site => site.id === 'mhh')
  await routing.getByLabel('Selection method').selectOption('coordinates')
  for (const [label, value] of [['Start longitude', origin.longitude], ['Start latitude', origin.latitude], ['End longitude', destination.longitude], ['End latitude', destination.latitude]])
    await routing.getByLabel(label).fill(String(value))
  const endpointBounds = await routing.locator('.endpoint-section').boundingBox()
  const flightControlsBounds = await routing.locator('.regional-controls').boundingBox()
  expect(endpointBounds.y + endpointBounds.height).toBeLessThan(flightControlsBounds.y)
  await expect(routing.locator('#endpoint-bounds')).toContainText('WGS84')
  await routing.getByLabel('Planning mode', { exact: true }).selectOption('research')
  await routing.getByLabel('Background score assumption').fill('0')
  expect(evidence.scenario_requests).toBe(1)
  const automaticResponse = page.waitForResponse(response => response.url().endsWith('/study/route'))
  clock = Date.now()
  await routing.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  const rawResponse = await automaticResponse
  const request = rawResponse.request().postDataJSON()
  const result = await rawResponse.json()
  evidence.automatic_route_ms = Date.now() - clock
  evidence.automatic_request = request
  evidence.automatic_result = result
  expect(result.status).toBe('success')
  expect(request.duration_mode).toBe('automatic')
  expect(request.scenario.mission_end).toBeUndefined()
  expect(result.timing.cruise_time_s).toBeCloseTo(result.length_m / request.scenario.speed_m_s, 8)
  expect(Math.abs(Date.parse(result.timing.estimated_arrival) - Date.parse(request.scenario.mission_start) - result.length_m / request.scenario.speed_m_s * 1000)).toBeLessThanOrEqual(1.01)
  expect(Date.parse(result.timing.assessed_interval.mission_end)).toBeGreaterThanOrEqual(Date.parse(result.timing.estimated_arrival))
  expect(result.mission.mission_end).toBe(result.timing.estimated_arrival)
  expect(result.restriction_report.assessed_interval).toEqual(result.timing.assessed_interval)
  expect(result.source_preparation_ms).toBeGreaterThan(0)
  expect(result.runtime_ms).toBeLessThan(110_000)
  await expect(routing.getByRole('region', { name: 'Flight time estimate' })).not.toContainText('Awaiting route')
  await expect(page.getByTestId('flight-interval-scope')).toHaveAttribute('data-assessed-end', result.timing.assessed_interval.mission_end)
  await routing.getByRole('region', { name: 'Flight time estimate' }).screenshot({ path: resolve(output, 'flight-time-desktop.png') })
  // Independent historical explicit-interval call on the same sources/controls.
  clock = Date.now()
  const baselineResponse = await page.request.post(`${process.env.UAS_API_URL}/api/datasets/hannover-part1-v4/study/route`, { data: { ...request, duration_mode: 'explicit', scenario: { ...request.scenario, ...result.timing.assessed_interval } }, timeout: 120_000 })
  expect(baselineResponse.ok()).toBe(true)
  const baseline = await baselineResponse.json()
  evidence.explicit_baseline_ms = Date.now() - clock
  evidence.explicit_baseline = { status: baseline.status, length_m: baseline.length_m, objective_cost: baseline.objective_cost, geometry_matches: JSON.stringify(baseline.geometry) === JSON.stringify(result.geometry) }
  expect(baseline.status).toBe('success')
  expect(baseline.geometry).toEqual(result.geometry)
  expect(baseline.length_m).toBeCloseTo(result.length_m, 7)
  expect(baseline.objective_cost).toBeCloseTo(result.objective_cost, 7)
  expect(baseline.provenance.model_signature).toBe(result.provenance.model_signature)
  const downloadPromise = page.waitForEvent('download')
  await routing.getByRole('button', { name: 'Export displayed result', exact: true }).click()
  const download = await downloadPromise
  await download.saveAs(resolve(output, 'automatic-route.geojson'))
  const exported = JSON.parse(await readFile(resolve(output, 'automatic-route.geojson'), 'utf8'))
  expect(exported.metadata.timing).toEqual(result.timing)
  expect(exported.metadata.mission).toEqual(result.mission)
  expect(exported.features[0].geometry).toEqual(result.geometry)
  expect(exported.metadata.displayed_controls.mission_end).toBeUndefined()
  clock = Date.now()
  await dipul.getByLabel('Unknown areas').check()
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  evidence.final_assessed_layers_ms = Date.now() - clock
  const finalBody = evidence.scenario_bodies.at(-1)
  expect(finalBody.duration_mode).toBe('explicit')
  expect(finalBody.scenario.mission_end).toBe(result.timing.assessed_interval.mission_end)
  await page.getByRole('button', { name: 'Focus destination', exact: true }).click()
  await centerClick()
  await expect(inspector).toContainText('Selected · DIPUL')
  await expect(inspector.getByRole('region', { name: 'Scenario assessment' })).toContainText(result.timing.assessed_interval.mission_end)
  await expect(map.locator('.leaflet-regional-route-pane path')).toHaveCount(1)
  await inspector.getByRole('button', { name: 'Clear selection', exact: true }).click()
  const preparedCount = evidence.scenario_requests
  for (let cycle = 0; cycle < 10; cycle++) {
    await dipul.getByLabel('Unknown areas').uncheck()
    await dipul.getByLabel('Unknown areas').check()
  }
  expect(evidence.scenario_requests).toBe(preparedCount)
  evidence.final_visibility_cycles = 10
  await page.setViewportSize({ width: 390, height: 844 })
  await routing.getByRole('region', { name: 'Flight time estimate' }).scrollIntoViewIfNeeded()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: resolve(output, 'flight-time-mobile.png') })
  await routing.locator('.endpoint-section').screenshot({ path: resolve(output, 'endpoints-mobile.png') })
  await dipul.getByLabel('Unknown areas').uncheck()
  await routing.getByLabel('Cruise speed').fill('35')
  await expect(routing.getByRole('region', { name: 'Flight time estimate' })).toContainText('Awaiting route')
  await expect(routing.getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
  await expect(map.locator('.leaflet-regional-route-pane path')).toHaveCount(0)
  expect(evidence.route_requests).toBe(2)
  expect(evidence.scenario_requests).toBe(2)
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
