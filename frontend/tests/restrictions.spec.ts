import { expect, test } from '@playwright/test'

test('default conservative policy, saved evidence revision, scoped request and invalidation', async ({ page }) => {
  const bounds = { west: 9.6, south: 52.2, east: 10.1, north: 52.5 }
  const dataset = { id: 'restrictions', has_study: true, verified: true, feature_count: 0, geometry_counts: {}, layer_counts: {}, crs: 'EPSG:4326', query_bounds: bounds, feature_bounds: null }
  const empty = { type: 'FeatureCollection', features: [] }
  const profiles: unknown[] = []
  const report = { counts: { prohibited: 0, conditional_allowed: 0, not_applicable: 0, unresolved: 1 }, decisions: [{ source: 'dipul:test/1', source_signature: 'original', state: 'unresolved', reason: 'No evidence' }], coverage: { status: 'unverified', reason: 'Coverage is not verified' }, policy_exclusions: 1 }
  let routeRequests = 0
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/restriction-profiles')) {
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON()
        expect(body.zone_assessments['dipul:test/1'].source_signature).toBe('original')
        expect(body.zone_assessments['dipul:test/1'].phase).toBe('launch')
        const saved = { ...body, id: 'a'.repeat(32) }; profiles.push(saved)
        return route.fulfill({ status: 201, json: saved })
      }
      return route.fulfill({ json: { profiles, errors: [] } })
    }
    if (path.endsWith('/study/layers/constraints')) return route.fulfill({ json: { blocked: empty, unknown: empty, excluded: empty, diagnostics: [], provenance: {}, interpretation: 'Fixture', restriction_report: report } })
    if (path.endsWith('/study/route')) {
      routeRequests++
      const body = route.request().postDataJSON()
      expect(body.planning_mode).toBe('conservative')
      expect(body.scenario.vertical_reference_policy).toBe('nhn_as_msl_assumption')
      expect(body.scenario.nhn_msl_offset_m).toBe(routeRequests === 1 ? 0 : 5)
      expect(body.profile_id).toBe('a'.repeat(32))
      return route.fulfill({ json: { status: 'invalid_endpoint', message: 'Policy exclusion', geometry: null, length_m: null, risk_length_cost: null, objective_cost: null, cruise_time_s: null, cruise_time_range_s: null, preparation_ms: 1, planner_ms: 0, endpoint_diagnostics: { start: { vertical_comparisons: [{ source: 'dipul:kontrollzonen/kontrollzonen.57', aircraft_comparison_bounds_m: [156.747, 156.747], zone_msl_bounds_m: { lower: 155.7, upper: 762 }, vertical_relation: 'overlap', vertical_reference_assumption: { policy: 'nhn_as_msl_assumption' } }] } }, research_assumptions: [], restriction_report: report } })
    }
    if (path.endsWith('/study')) return route.fulfill({ json: { config: { bounds, locations: [{ id: 'rheuma-podbi', name: 'Origin', longitude: 9.7, latitude: 52.3 }, { id: 'mhh', name: 'MHH', longitude: 9.8, latitude: 52.3 }] }, sources: {} } })
    if (path === '/api/terrain-datasets') return route.fulfill({ json: { datasets: [{ id: 'hannover-part2-terrain-v1', tiles: 120 }] } })
    return route.fulfill({ json: path === '/api/datasets' ? { datasets: [dataset] } : dataset })
  })
  await page.goto('/')
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await expect(panel.getByLabel('Planning mode', { exact: true })).toHaveValue('conservative')
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  await panel.getByRole('button', { name: 'Load scenario layers' }).click()
  await panel.getByText('Restriction assessments and reviewed notices', { exact: true }).click()
  await panel.getByLabel('Profile name', { exact: true }).fill('Reviewed launch consent')
  await panel.getByLabel('Assessed zone', { exact: true }).selectOption('dipul:test/1')
  await panel.getByLabel('Assessment decision', { exact: true }).selectOption('conditional_allowed')
  await panel.getByLabel('Permission phase', { exact: true }).selectOption('launch')
  await panel.getByLabel('Assessment evidence', { exact: true }).fill('Synthetic permission document')
  await panel.getByLabel('Satisfied conditions').fill('Synthetic condition verified')
  await panel.getByRole('button', { name: 'Add assessment to draft' }).click()
  await panel.getByRole('button', { name: 'Save and use profile revision' }).click()
  await expect(panel.getByLabel('Restriction profile', { exact: true })).toHaveValue('a'.repeat(32))
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('Policy exclusion')
  await expect(panel.getByRole('status')).toContainText('aircraft 156.747–156.747 m MSL comparison')
  await panel.getByLabel('NHN to MSL offset (m)', { exact: true }).fill('5')
  await expect(panel.getByRole('status')).toHaveCount(0)
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('Policy exclusion')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:20')
  await expect(panel.getByRole('status')).toHaveCount(0)
  expect(routeRequests).toBe(2)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await panel.screenshot({ path: '../.cache/iteration010-profile-mobile.png' })
})
