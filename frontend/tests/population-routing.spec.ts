import { expect, test, type Page, type Route } from '@playwright/test'
import { setup } from './fixtures/regionalSelection'
import { timedResult } from './fixtures/flightInterval'

interface Request {
  objective: string; include_population: boolean; population_weight?: number
  risk_weight: number; distance_weight: number
  scenario: { mission_start: string; speed_m_s: number }
}
const panel = (page: Page) => page.getByRole('region', { name: 'Regional route planning', exact: true })
const estimate = (page: Page) => page.getByRole('region', { name: 'Flight time estimate', exact: true })
const submit = (page: Page) => panel(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
function response(body: Request) {
  const active = body.include_population && (body.population_weight ?? 0) > 0
  const building = body.objective === 'risk'
  return timedResult(body, {
    status: 'success', geometry: { type: 'LineString', coordinates: [[9.8, 52.388], [9.805, 52.388]] },
    length_m: 1000, risk_length_cost: building ? 20 : null, population_length_cost: active ? 350 : null,
    objective_cost: (building ? body.risk_weight * 20 + body.distance_weight * 1000 : 1000) + (active ? body.population_weight! * 350 : 0),
    effective_objective: body.objective + (active ? '+population' : ''),
    effective_weights: { building: building ? body.risk_weight : 0, distance: building ? body.distance_weight : 1, population: active ? body.population_weight : 0 },
    population_active: active, population_assessment: active ? 'assessed' : 'not_evaluated',
    population_model: active ? { identity: 'fixed-study-population', version: 'ramke-population-250m-v1' } : null,
    cruise_time_s: 1000 / 30, cruise_time_range_s: [1000 / 35, 40], preparation_ms: 20, planner_ms: 5,
    endpoint_diagnostics: {}, research_assumptions: [],
    provenance: { population_model_identity: active ? 'fixed-study-population' : null },
    controls: { include_population: body.include_population, population_weight: body.include_population ? body.population_weight : null },
  })
}
async function fixture(page: Page, respond?: (route: Route, body: Request) => Promise<void>) {
  const requests: Request[] = []
  const state = await setup(page, async (route, path) => {
    if (!path.endsWith('/study/route')) return false
    const body: Request = route.request().postDataJSON()
    requests.push(body)
    if (respond) await respond(route, body)
    else await route.fulfill({ json: response(body) })
    return true
  })
  await panel(page).getByLabel('Departure time').fill('2026-10-07T10:00')
  return { ...state, requests }
}
async function exported(page: Page) {
  const download = page.waitForEvent('download')
  await panel(page).getByRole('button', { name: 'Export displayed result' }).click()
  const stream = await (await download).createReadStream()
  let content = ''
  for await (const chunk of stream!) content += chunk.toString()
  return JSON.parse(content)
}

test('population defaults off; enabling clears route/ETA without solving or loading display data', async ({ page }) => {
  const { requests, calls, errors } = await fixture(page)
  const toggle = panel(page).getByLabel('Include population', { exact: true })
  await expect(toggle).not.toBeChecked()
  await expect(panel(page).getByLabel('Population weight', { exact: true })).toHaveCount(0)
  await submit(page)
  await expect(estimate(page)).not.toContainText('Awaiting route')
  expect(requests[0]).toMatchObject({ objective: 'risk', include_population: false, risk_weight: 0.9, distance_weight: 0.1 })
  expect(requests[0]).not.toHaveProperty('population_weight')
  await expect(panel(page)).toContainText('Population assessment: Not evaluated (inactive)')
  await toggle.check()
  await expect(panel(page).getByLabel('Population weight', { exact: true })).toHaveValue('1')
  await expect(estimate(page)).toContainText('Awaiting route')
  await expect(panel(page).getByRole('status')).toHaveCount(0)
  await expect(panel(page).getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
  expect(requests).toHaveLength(1)
  expect(calls.urls.some(url => /\/study\/population(?:-costs)?(?:\?|$)/.test(url))).toBe(false)
  expect(errors).toEqual([])
})

for (const objective of ['risk', 'distance']) {
  test(`${objective} plus population displays separate effective costs and exports the displayed result`, async ({ page }) => {
    const { requests, calls } = await fixture(page)
    await panel(page).getByLabel('Objective', { exact: true }).selectOption(objective)
    await panel(page).getByLabel('Include population', { exact: true }).check()
    await panel(page).getByLabel('Population weight', { exact: true }).fill('0.25')
    await submit(page)
    await expect(panel(page).getByRole('region', { name: 'Route costs' })).toContainText('Population cost 350.00 score-metres')
    await expect(panel(page)).toContainText(objective === 'risk' ? 'Building risk + population' : 'Distance + population')
    await expect(panel(page)).toContainText(`Effective weights: building ${objective === 'risk' ? '0.9' : '0'} · distance ${objective === 'risk' ? '0.1' : '1'} · population 0.25`)
    const costs = panel(page).getByRole('region', { name: 'Route costs' })
    await expect(costs).toContainText(`Objective cost ${objective === 'risk' ? '205.50' : '1087.50'}`)
    if (objective === 'risk') await expect(costs).toContainText('Building cost 20.00 score-metres')
    else await expect(costs).not.toContainText('Building cost')
    expect(requests[0]).toMatchObject({ objective, include_population: true, population_weight: 0.25 })
    expect(calls.urls.some(url => url.includes('/study/population'))).toBe(false)
    const data = await exported(page)
    expect(data.metadata.population_model.identity).toBe('fixed-study-population')
    expect(data.metadata.population_length_cost).toBe(350)
    expect(data.metadata.displayed_controls).toMatchObject({ include_population: true, population_weight: '0.25' })
    expect(data.features[0].properties).toMatchObject({ length_m: 1000, population_length_cost: 350, effective_objective: `${objective}+population`, effective_weights: { population: 0.25 } })
    expect(requests).toHaveLength(1)
    // The inspection overlay never enables/disables the routing objective or clears its result.
    const display = page.getByLabel('GHSL — population risk (250 m)', { exact: true })
    await display.check()
    await expect(page.getByTestId('population-cost-state')).toContainText('Ready')
    await display.uncheck()
    await expect(costs).toContainText('Population cost 350.00')
    await expect(panel(page).getByLabel('Include population', { exact: true })).toBeChecked()
    expect(requests).toHaveLength(1)
    await panel(page).getByLabel('Population weight', { exact: true }).fill('2')
    await expect(estimate(page)).toContainText('Awaiting route')
    await expect(panel(page).getByRole('status')).toHaveCount(0)
    expect(requests).toHaveLength(1)
  })
}

test('empty/negative weights block active submission, hidden values are ignored, and zero stays inactive', async ({ page }) => {
  const { requests } = await fixture(page)
  const toggle = panel(page).getByLabel('Include population', { exact: true })
  await toggle.check()
  for (const invalid of ['', '-1']) {
    await panel(page).getByLabel('Population weight', { exact: true }).fill(invalid)
    await submit(page)
    expect(requests).toHaveLength(0)
  }
  await toggle.uncheck()
  await submit(page)
  await expect(panel(page).getByRole('status')).toContainText('success')
  expect(requests[0]).not.toHaveProperty('population_weight')
  await toggle.check()
  await expect(panel(page).getByLabel('Population weight', { exact: true })).toHaveValue('-1')
  await panel(page).getByLabel('Population weight', { exact: true }).fill('0')
  await submit(page)
  await expect(panel(page)).toContainText('Population assessment: Not evaluated (inactive)')
  await expect(panel(page).getByRole('region', { name: 'Route costs' })).not.toContainText('Population cost')
  expect(requests[1]).toMatchObject({ include_population: true, population_weight: 0 })
  expect((await exported(page)).metadata.population_length_cost).toBeNull()
})

for (const edit of ['checkbox', 'weight']) {
  test(`editing population ${edit} cancels a delayed solve and prevents stale route/ETA`, async ({ page }) => {
    let release!: () => void, finished!: () => void
    const gate = new Promise<void>(resolve => { release = resolve })
    const done = new Promise<void>(resolve => { finished = resolve })
    const { requests } = await fixture(page, async (route, body) => {
      await gate
      await route.fulfill({ json: response(body) }).catch(() => {})
      finished()
    })
    await panel(page).getByLabel('Include population', { exact: true }).check()
    await submit(page)
    await expect.poll(() => requests.length).toBe(1)
    if (edit === 'checkbox') await panel(page).getByLabel('Include population', { exact: true }).uncheck()
    else await panel(page).getByLabel('Population weight', { exact: true }).fill('2')
    await expect(panel(page).getByRole('button', { name: 'Plan regional route', exact: true })).toBeEnabled()
    release()
    await done
    await expect(estimate(page)).toContainText('Awaiting route')
    await expect(panel(page).getByRole('status')).toHaveCount(0)
    expect(requests).toHaveLength(1)
  })
}

test('unresolved population is diagnostic only; failed export has no geometry or measured costs', async ({ page }) => {
  await fixture(page, async (route, body) => {
    await route.fulfill({ json: { ...response(body), status: 'unresolved_input', message: 'Population endpoint support is unknown.', geometry: null, length_m: null, risk_length_cost: null, population_length_cost: null, objective_cost: null, cruise_time_s: null, timing: undefined, population_assessment: 'unresolved', endpoint_diagnostics: { start: { population: { assessment: 'unresolved', population_unknown_cell_ids: ['population250:0:1'] } } } } })
  })
  await panel(page).getByLabel('Include population', { exact: true }).check()
  await submit(page)
  await expect(panel(page).getByRole('status')).toContainText('Population endpoint support is unknown.')
  await expect(panel(page).getByRole('status')).toContainText('population250:0:1')
  await expect(panel(page).getByRole('region', { name: 'Route costs' })).toHaveCount(0)
  await expect(estimate(page)).toContainText('Awaiting route')
  const data = await exported(page)
  expect(data.features).toEqual([])
  expect(data.metadata.population_length_cost).toBeNull()
  expect(data.metadata.population_assessment).toBe('unresolved')
})

test('population controls fit mobile and preserve the selected weight across objective changes', async ({ page }) => {
  await fixture(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await panel(page).getByLabel('Include population', { exact: true }).check()
  await panel(page).getByLabel('Population weight', { exact: true }).fill('2.5')
  await panel(page).getByLabel('Objective', { exact: true }).selectOption('distance')
  await expect(panel(page).getByLabel('Risk weight', { exact: true })).toHaveCount(0)
  await expect(panel(page).getByLabel('Population weight', { exact: true })).toHaveValue('2.5')
  await expect(panel(page)).toContainText('Distance + population: length + weight')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await panel(page).screenshot({ path: '../.cache/iteration014-part3-mobile.png' })
  await page.setViewportSize({ width: 1440, height: 1000 })
  await panel(page).screenshot({ path: '../.cache/iteration014-part3-desktop.png' })
})
