import { expect, test } from '@playwright/test'

test('regional controls preserve weighted defaults, invalidate results and export without another solve', async ({ page }) => {
  let requests = 0
  const dataset = { id: 'regional', has_study: true, verified: true, feature_count: 0, geometry_counts: {}, layer_counts: {}, crs: 'EPSG:4326', query_bounds: { west: 10.51, south: 52.26, east: 10.53, north: 52.28 }, feature_bounds: null }
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/study/route')) {
      requests++
      const body = route.request().postDataJSON()
      expect(body.objective).toBe('risk')
      expect(body.risk_weight).toBe(0.9)
      expect(body.scenario.agl_m).toBe(100)
      expect(body.background_cost).toBeNull()
      return route.fulfill({ json: { status: 'unresolved_input', message: 'Missing building heights', geometry: null, length_m: null, risk_length_cost: null, objective_cost: null, cruise_time_s: null, cruise_time_range_s: null, preparation_ms: 40000, planner_ms: 0, endpoint_diagnostics: {}, research_assumptions: [], provenance: { signature: 'fixture' } } })
    }
    if (path.endsWith('/study')) return route.fulfill({ json: { config: { bounds: dataset.query_bounds, locations: [{ id: 'mhh', name: 'MHH', longitude: 10.52, latitude: 52.27 }, { id: 'rheuma-podbi', name: 'Rheuma Podbi', longitude: 10.51, latitude: 52.26 }] }, sources: {} } })
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : path.endsWith('/features') ? { type: 'FeatureCollection', features: [] } : dataset })
  })
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  await panel.getByRole('button', { name: 'Plan regional route' }).click()
  await expect(panel.getByRole('status')).toContainText('Missing building heights')
  const download = page.waitForEvent('download')
  await panel.getByRole('button', { name: 'Export displayed result' }).click()
  await download
  expect(requests).toBe(1)
  await panel.getByLabel('Cruise speed').fill('35')
  await expect(panel.getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
  await panel.getByLabel('Objective', { exact: true }).selectOption('distance')
  await expect(panel.getByLabel('Risk weight', { exact: true })).toHaveCount(0)
  await panel.getByLabel('Objective', { exact: true }).selectOption('risk')
  await expect(panel.getByLabel('Risk weight', { exact: true })).toHaveValue('0.9')
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await panel.screenshot({ path: '../.cache/part3-mobile.png' })
})

test('eight catalog endpoints, independent layers, successful route export and parameter invalidation', async ({ page }) => {
  const ids = ['mhh', 'henriettenstift', 'rheuma-lister', 'rheuma-podbi', 'limbach-lehrte', 'amedes-georg', 'amedes-schiffgraben', 'friederikenstift']
  const bounds = { west: 9.6, south: 52.2, east: 10.1, north: 52.5 }
  const dataset = { id: 'hannover', has_study: true, verified: true, feature_count: 0, geometry_counts: {}, layer_counts: {}, crs: 'EPSG:4326', query_bounds: bounds, feature_bounds: null }
  const sites = ids.map((id, index) => ({ id, name: `Site ${id}`, longitude: 9.7 + index * 0.02, latitude: 52.3 }))
  const empty = { type: 'FeatureCollection', features: [] }
  let solves = 0
  const loaded: string[] = []
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    loaded.push(path)
    if (path.endsWith('/study/route')) {
      solves++
      return route.fulfill({ json: { status: 'success', geometry: { type: 'LineString', coordinates: [[9.76, 52.3], [9.7, 52.3]] }, length_m: 1000, risk_length_cost: 20, objective_cost: 118, cruise_time_s: 1000 / 30, cruise_time_range_s: [1000 / 35, 40], preparation_ms: 20, planner_ms: 5, runtime_ms: 25, research_assumptions: [], endpoint_diagnostics: {}, provenance: { model_signature: 'retained-source' }, mission: { speed_m_s: 30 } } })
    }
    if (path.endsWith('/study/layers/constraints')) return route.fulfill({ json: { blocked: empty, unknown: empty, diagnostics: [{ reason: 'Fixture uncertainty' }], provenance: {}, interpretation: 'No permission inferred' } })
    if (path.endsWith('/study/population')) return route.fulfill({ json: { layer: empty } })
    if (path.endsWith('/study/layers/zones') || path.endsWith('/features')) return route.fulfill({ json: empty })
    if (path.endsWith('/study')) return route.fulfill({ json: { config: { bounds, locations: sites }, sources: {} } })
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : dataset })
  })
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await expect(panel.getByLabel('Origin', { exact: true }).locator('option')).toHaveCount(8)
  await expect(panel.getByLabel('Destination', { exact: true }).locator('option')).toHaveCount(8)
  await expect(page.getByRole('region', { name: 'Hannover regional map' })).toBeVisible()
  await panel.getByLabel('Destination', { exact: true }).selectOption('rheuma-podbi')
  await expect(panel).toContainText('same address')
  await panel.getByLabel('Destination', { exact: true }).selectOption('mhh')
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  await panel.getByRole('button', { name: 'Load scenario layers' }).click()
  await expect(page.getByText('Layer coverage and applicability findings')).toBeVisible()
  await page.getByLabel('Original DIPUL').check()
  await page.getByLabel('GHSL —').check()
  await expect.poll(() => loaded.includes('/api/datasets/hannover/study/population')).toBe(true)
  await page.getByLabel('Original DIPUL').uncheck()
  await expect(page.getByLabel('GHSL —')).toBeChecked()
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('Length 1000.0 m')
  const downloadPromise = page.waitForEvent('download')
  await panel.getByRole('button', { name: 'Export displayed result' }).click()
  const download = await downloadPromise
  const stream = await download.createReadStream()
  let content = ''
  for await (const chunk of stream!) content += chunk.toString()
  const exported = JSON.parse(content)
  expect(exported.metadata.provenance.model_signature).toBe('retained-source')
  expect(exported.metadata.catalog_endpoints).toHaveLength(2)
  expect(exported.features[0].geometry.type).toBe('LineString')
  expect(solves).toBe(1)
  await panel.getByLabel('Altitude AGL').fill('120')
  await expect(panel.getByRole('status')).toHaveCount(0)
  await expect(page.getByText('Layer coverage and applicability findings')).toHaveCount(0)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: '../.cache/part4-mobile.png', fullPage: true })
})
