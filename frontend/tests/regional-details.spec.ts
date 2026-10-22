import { expect, test } from '@playwright/test'
import { detail, detailView, geometry, setup, inspector, osm, map, centerClick, empty } from './fixtures/regionalSelection'

test('OSM source facts preserve heights, address, independent costs, defaults and safely nested original tags', async ({ page }) => {
  const attack = '<img src=x onerror="window.sourceExecuted=true">'
  const long = 'source-value-'.repeat(60)
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/osm/features/node/1')) return false
    const score = { status: 'known', has_default: false, obstruction: false, rule_version: 'test-rules', tags: [] }
    await route.fulfill({ json: { ...detail('node/1'), properties: { element_type: 'node', osm_id: 1, name: attack, building: 'hospital', height: '30 ft', min_height: 0, 'building:levels': 3, 'addr:street': 'Test Street', 'addr:housenumber': '12', 'addr:city': 'Hannover', nested: { values: [0, false, null, attack, long] } }, display: { ...detail('node/1').display, categories: ['building', 'landuse'] }, layer_analyses: {
      building: { ...score, cost: 4, label: 'Very high', has_default: true, obstruction: true, tags: [{ key: 'building', value: ['hospital', 'unrecognized'], cost: 4, status: 'mixed', has_default: true, matches: [{ normalized: 'hospital', status: 'matched', cost: 4, reason: 'Known hospital rule', source: 'Test reference, p. 7' }], reason: 'Default included', source: 'Test rules' }] },
      landuse: { ...score, cost: 1, label: 'Low' },
    } } })
    return true
  })
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  const panel = inspector(page)
  await expect(panel.getByRole('heading', { name: attack, exact: true })).toBeVisible()
  const facts = panel.getByRole('region', { name: 'Original source facts' })
  await expect(facts).toContainText('30 ft')
  await expect(facts).toContainText('0 m')
  await expect(facts).toContainText('3 · levels, not a measured height')
  await expect(facts).toContainText('Test Street 12 Hannover')
  await expect(facts).toContainText('Buildings, Land use')
  await expect(panel).toContainText('Building cost: 4 · Very high')
  await expect(panel).toContainText('Land use cost: 1 · Low')
  await expect(panel).toContainText('Provisional · includes unknown/default values')
  await expect(panel).toContainText('Historical paper obstruction flag')
  await panel.getByText('Matched rules and evidence', { exact: true }).first().click()
  await expect(panel.getByText('Known hospital rule', { exact: true })).toBeVisible()
  await panel.getByText('Original tags', { exact: true }).click()
  await expect(panel.getByText(long, { exact: true }).first()).toBeVisible()
  await expect(panel.getByText('No', { exact: true })).toBeVisible()
  await expect(panel.getByText('Not supplied', { exact: true }).first()).toBeVisible()
  await expect(panel.locator('img, script')).toHaveCount(0)
  await expect(panel.locator('.source-raw pre')).not.toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(await page.evaluate(() => 'sourceExecuted' in window)).toBe(false)
})

test('missing OSM facts remain absent rather than becoming measured zeroes or supplied costs', async ({ page }) => {
  await setup(page)
  await detailView(page)
  await osm(page).getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(inspector(page)).toContainText('Height not supplied by original tags')
  await expect(inspector(page)).toContainText('No category cost analysis supplied')
  await expect(inspector(page).getByRole('region', { name: 'Original source facts' })).not.toContainText('0 m')
  await expect(inspector(page).locator('.source-raw pre')).not.toBeVisible()
})

for (const [name, value, expected] of [['zero', 0, 'Estimated population: 0 people per native cell'], ['NoData', null, 'NoData · population unavailable'], ['small positive', 0.00001, 'Estimated population: less than 0.01 people per native cell']] as const)
  test(`GHSL ${name} is distinguished with native units, epoch and query coverage`, async ({ page }) => {
    await setup(page, async (route, path) => {
      if (!path.endsWith('/study/population')) return false
      await route.fulfill({ json: { product: 'GHS-POP test', epoch: 2020, native_support_m: 100, complete_support: false, layer: { type: 'FeatureCollection', features: [{ type: 'Feature', id: '10:20', geometry, properties: { people_per_cell: value, status: value == null ? 'unknown' : 'known' } }] } } })
      return true
    })
    await osm(page).getByLabel('Show saved OSM').uncheck()
    await page.getByLabel('GHSL — population cells', { exact: true }).check()
    const group = page.getByRole('region', { name: 'GHSL population', exact: true })
    await expect(group).toContainText('Ready · 1 cells')
    await centerClick(page)
    await expect(inspector(page)).toContainText(expected)
    await expect(inspector(page)).toContainText('100 m × 100 m')
    await expect(inspector(page)).toContainText('2020')
    await expect(inspector(page)).toContainText('GHS-POP test')
    await expect(inspector(page)).toContainText('incomplete population support')
    await expect(group.locator('.cost-legend span').filter({ hasText: /^Zero$/ }).locator('i')).toHaveCSS('background-color', 'rgb(241, 249, 235)')
    await expect(group.locator('.cost-legend span').filter({ hasText: /^NoData$/ }).locator('i')).toHaveCSS('background-color', 'rgb(116, 123, 134)')
    await expect(map(page).locator('.selection-summary')).toContainText(expected)
    if (value == null) await expect(inspector(page)).toContainText('Missing population data is not zero')
    else if (value === 0) await expect(inspector(page)).toContainText('Known zero estimate')
  })

test('DIPUL assessment separates policy, original limits, scoped height/time and nested provenance', async ({ page }) => {
  const reason = '<script>source reason</script>'
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/layers/constraints')) return false
    await route.fulfill({ json: { blocked: empty, unknown: empty, excluded: { type: 'FeatureCollection', features: [{ type: 'Feature', id: 'zone/1', geometry, properties: { source: 'dipul:test/1', name: 'Test zone', state: 'unresolved', reason, policy_exclusion: true, clearance_m: 0, lower_limit_altitude: 0, lower_limit_unit: 'ft', lower_limit_alt_ref: 'AGL', upper_limit_altitude: 300, upper_limit_unit: 'm', upper_limit_alt_ref: 'MSL', legal_reference: 'Supplied source reference', valid_from: '2026-10-07T00:00:00+02:00', valid_until: '2026-10-08T00:00:00+02:00', evidence: { conditions: ['condition A', 'condition B'], source: 'review note' } } }] }, diagnostics: [], provenance: { model_signature: 'model-test', scenario: { mission_start: '2026-10-07T10:00:00+02:00', mission_end: '2026-10-07T10:15:00+02:00', agl_m: 100 } }, interpretation: 'Test' } })
    return true
  })
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await page.getByLabel('Scenario start', { exact: true }).fill('2026-10-07T10:00')
  await page.getByLabel('Scenario end', { exact: true }).fill('2026-10-07T10:15')
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  await centerClick(page)
  const assessment = inspector(page).getByRole('region', { name: 'Scenario assessment' })
  await expect(assessment).toContainText('Policy exclusion · unresolved')
  await expect(assessment).toContainText('not a confirmed prohibition')
  await expect(assessment).toContainText(reason)
  await expect(assessment).toContainText('100 m AGL')
  await expect(assessment).toContainText('10:15:00+02:00')
  await expect(assessment).toContainText('0 m')
  const original = inspector(page).getByRole('region', { name: 'Source record' })
  await expect(original).toContainText('0 ft · AGL')
  await expect(original).toContainText('300 m · MSL')
  await expect(original).toContainText('Supplied source reference')
  await expect(original).not.toContainText('100 m AGL')
  await inspector(page).getByText('Assessment attributes', { exact: true }).click()
  await expect(inspector(page).getByText('condition A', { exact: true })).toBeVisible()
  await expect(inspector(page).locator('script')).toHaveCount(0)
  await expect(inspector(page).locator('.source-raw pre')).not.toBeVisible()
})

test('missing DIPUL limits never imply zero height, and color help explains display changes and overview limits', async ({ page }) => {
  const { calls } = await setup(page)
  await expect(osm(page).getByLabel('OSM color view')).toHaveValue('category')
  await expect(osm(page)).toContainText('first enabled category')
  await osm(page).getByLabel('OSM color view').selectOption({ label: 'Category cost' })
  await expect(osm(page)).toContainText('not an overall risk surface')
  await expect(osm(page)).toContainText('does not change the route objective')
  await expect(osm(page)).toContainText('overview cells have no cost score')
  await expect(osm(page)).toContainText('does not acquire new OSM originals')
  await expect(osm(page).getByLabel('OSM legend')).toContainText('Buildings')
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await page.getByLabel('Scenario start', { exact: true }).fill('2026-10-07T10:00')
  await page.getByLabel('Scenario end', { exact: true }).fill('2026-10-07T10:15')
  await expect(page.getByTestId('dipul-layer-state')).toContainText('Ready')
  await centerClick(page)
  await expect(inspector(page).getByRole('region', { name: 'Source record' })).toContainText('Lower limitNot suppliedUpper limitNot supplied')
  expect(calls.routes).toBe(0)
})

test('scenario coverage remains an uncertainty finding with a supplied scope rather than a source-zone ban', async ({ page }) => {
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/layers/constraints')) return false
    await route.fulfill({ json: { blocked: empty, excluded: empty, unknown: { type: 'FeatureCollection', features: [{ type: 'Feature', id: 'coverage/1', geometry, properties: { source: 'regional coverage', state: 'unresolved', reason: 'Temporary coverage remains unverified.', scope: 'region-wide applicability uncertainty', policy_exclusion: false } }] }, diagnostics: [], provenance: {}, interpretation: 'Coverage is not permission.' } })
    return true
  })
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await page.getByLabel('Scenario start', { exact: true }).fill('2026-10-07T10:00')
  await page.getByLabel('Scenario end', { exact: true }).fill('2026-10-07T10:15')
  await page.getByRole('region', { name: 'Scenario coverage & diagnostics', exact: true }).getByLabel('Unknown areas').check()
  await expect(page.getByTestId('coverage-layer-state')).toContainText('Ready')
  await centerClick(page)
  await expect(inspector(page)).toContainText('Selected · Scenario')
  const assessment = inspector(page).getByRole('region', { name: 'Scenario assessment' })
  await expect(assessment).toContainText('Unresolved assessment')
  await expect(assessment).toContainText('not a confirmed prohibition')
  await expect(assessment).toContainText('region-wide applicability uncertainty')
  await expect(assessment).toContainText('Assessed time and flight-height scope not supplied')
})

test('derived building findings retain source identity, clearance and a validated original-object link', async ({ page }) => {
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/layers/constraints')) return false
    await route.fulfill({ json: { blocked: { type: 'FeatureCollection', features: [{ type: 'Feature', id: 'building/1', geometry, properties: { source: 'way/22', category: 'building_obstacle', state: 'blocked', reason: 'missing height; conservative footprint assumption', clearance_m: 0, buffer_m: 15 } }] }, unknown: empty, excluded: empty, diagnostics: [], provenance: {}, interpretation: 'Test building' } })
    return true
  })
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await page.getByLabel('Scenario start', { exact: true }).fill('2026-10-07T10:00')
  await page.getByLabel('Scenario end', { exact: true }).fill('2026-10-07T10:15')
  await expect(page.getByTestId('osm-layer-state')).toContainText('Ready')
  await centerClick(page)
  await expect(inspector(page)).toContainText('Building obstacle')
  await expect(inspector(page)).toContainText('15 m')
  await expect(inspector(page)).toContainText('conservative footprint assumption')
  await expect(inspector(page).getByRole('link', { name: 'View original OSM way/22 ↗', exact: true })).toHaveAttribute('href', 'https://www.openstreetmap.org/way/22')
})
