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
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : path.endsWith('/features') ? { type: 'FeatureCollection', features: [] } : dataset })
  })
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00:00+02:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15:00+02:00')
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
