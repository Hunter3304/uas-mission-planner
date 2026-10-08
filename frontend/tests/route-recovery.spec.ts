import { expect, test } from '@playwright/test'

test('scenario validation, explicit research assumptions and endpoint selection reach the API', async ({ page }) => {
  const bounds = { west: 9.7, south: 52.3, east: 9.9, north: 52.5 }
  const dataset = { id: 'hannover', has_study: true, verified: true, feature_count: 0, geometry_counts: {}, layer_counts: {}, crs: 'EPSG:4326', query_bounds: bounds, feature_bounds: null }
  let requests = 0
  let submitted: Record<string, unknown> = {}
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/terrain-datasets') return route.fulfill({ json: { datasets: [{ id: 'hannover-part2-terrain-v1', tiles: 120 }] } })
    if (path.endsWith('/study/route')) {
      requests++
      submitted = route.request().postDataJSON()
      return route.fulfill({ json: { status: 'success', geometry: { type: 'LineString', coordinates: [[9.796, 52.404], [9.804, 52.383]] }, length_m: 3000, risk_length_cost: 0, objective_cost: 300, cruise_time_s: 100, cruise_time_range_s: [3000 / 35, 120], preparation_ms: 100, planner_ms: 20, endpoint_diagnostics: {}, research_assumptions: [{ reason: 'Explicit research assumptions' }] } })
    }
    if (path.endsWith('/study')) return route.fulfill({ json: { config: { bounds, locations: [{ id: 'rheuma-podbi', name: 'Podbi', longitude: 9.796, latitude: 52.404 }, { id: 'mhh', name: 'MHH', longitude: 9.804, latitude: 52.383 }] }, sources: {} } })
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : dataset })
  })
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await expect(panel.getByLabel('Terrain dataset')).toContainText('120 tiles')
  await panel.getByLabel('Scenario start').fill('2026-10-08T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-08T09:00')
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('alert')).toContainText('after start')
  expect(requests).toBe(0)
  await panel.getByLabel('Scenario end').fill('2026-10-08T10:15')
  await panel.getByLabel('Planning mode').selectOption('research')
  await panel.getByLabel('Background score assumption').fill('0')
  await panel.getByLabel('Use explicitly selected launch/landing coordinates').check()
  await panel.getByLabel('Launch longitude').fill('9.796')
  await panel.getByLabel('Launch latitude').fill('52.404')
  await panel.getByLabel('Landing longitude').fill('9.804')
  await panel.getByLabel('Landing latitude').fill('52.383')
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('Length 3000.0 m')
  expect(submitted.scenario).toMatchObject({ mission_start: '2026-10-08T10:00:00+02:00', mission_end: '2026-10-08T10:15:00+02:00', research_geometry: 'derived', research_height_m: 30 })
  expect(submitted.start_coordinate).toEqual([9.796, 52.404])
  expect(submitted.background_cost).toBe(0)
  await panel.getByLabel('Missing building height estimate').fill('40')
  await expect(panel.getByRole('status')).toHaveCount(0)
  expect(requests).toBe(1)
})
