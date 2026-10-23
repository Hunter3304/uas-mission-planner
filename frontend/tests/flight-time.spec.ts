import { expect, test, type Page } from '@playwright/test'
import { setup, empty, geometry } from './fixtures/regionalSelection'
import { previewResult, timedResult } from './fixtures/flightInterval'
import { berlinDisplay } from '../src/scenarioTime'

const routing = (page: Page) => page.getByRole('region', { name: 'Regional route planning', exact: true })
const estimate = (page: Page) => page.getByRole('region', { name: 'Flight time estimate', exact: true })
const success = { status: 'success', geometry, length_m: 3600, risk_length_cost: 0, objective_cost: 3600, cruise_time_s: 120, cruise_time_range_s: [3600 / 35, 144], preparation_ms: 20, planner_ms: 2, endpoint_diagnostics: {}, research_assumptions: [] }
const layer = { blocked: empty, unknown: empty, excluded: empty, diagnostics: [], interpretation: 'Synthetic inspection', provenance: {} }

test('departure-only request uses actual cruise arrival; completed assessment refreshes layers and export', async ({ page }) => {
  const requests: Record<string, unknown>[] = []
  await setup(page, async (route, path) => {
    if (path.endsWith('/study/layers/constraints')) { const body = route.request().postDataJSON(); requests.push(body); await route.fulfill({ json: previewResult(body, layer) }); return true }
    if (path.endsWith('/study/route')) {
      const body = route.request().postDataJSON()
      expect(body.duration_mode).toBe('automatic')
      expect(body.scenario).not.toHaveProperty('mission_end')
      const response = timedResult(body, success)
      if ('timing' in response) response.timing.assessed_interval = { mission_start: body.scenario.mission_start, mission_end: '2026-10-07T10:03:00+02:00' }
      await route.fulfill({ json: response }); return true
    }
    return false
  })
  await expect(estimate(page)).toContainText('Awaiting route')
  await expect(routing(page).getByLabel('Scenario end')).toHaveCount(0)
  await routing(page).getByLabel('Departure time').fill('2026-10-07T10:00')
  await expect.poll(() => requests.length).toBe(1)
  await expect(page.getByTestId('flight-interval-scope')).toContainText('Provisional preview')
  await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(estimate(page)).toContainText('2026-10-07 10:02:00.000 +02:00')
  await expect(estimate(page)).toContainText('3600.0 m ÷ 30 m/s = 120.000 s')
  await expect.poll(() => requests.length).toBe(2)
  expect(requests[1]).toMatchObject({ duration_mode: 'explicit', scenario: { mission_end: '2026-10-07T10:03:00+02:00' } })
  await expect(page.getByTestId('flight-interval-scope')).toContainText('Completed route assessment')
  const download = page.waitForEvent('download')
  await routing(page).getByRole('button', { name: 'Export displayed result' }).click()
  const stream = await (await download).createReadStream(); let text = ''
  for await (const chunk of stream!) text += chunk.toString()
  const exported = JSON.parse(text)
  expect(exported.metadata.timing.estimated_arrival).toBe(exported.metadata.mission.mission_end)
  expect(exported.metadata.timing.cruise_time_s).toBe(120)
  expect(exported.metadata.displayed_controls).not.toHaveProperty('mission_end')
  await routing(page).getByLabel('Cruise speed').fill('35')
  await expect(estimate(page)).toContainText('Awaiting route')
  await expect(routing(page).getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
})

for (const [departure, expected] of [['2026-03-29T01:59:30', '2026-03-29 03:01:30.000 +02:00'], ['2026-10-07T23:59:30', '2026-10-08 00:01:30.000 +02:00']])
  test(`cruise arrival crosses UTC/calendar boundaries from ${departure}`, async ({ page }) => {
    await setup(page, async (route, path) => { if (!path.endsWith('/study/route')) return false; await route.fulfill({ json: timedResult(route.request().postDataJSON(), success) }); return true })
    await routing(page).getByLabel('Departure time').fill(departure)
    await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
    await expect(estimate(page)).toContainText(expected)
  })

test('fallback offset and fractional arrival formatting use the returned instant', () => {
  expect(berlinDisplay('2026-10-25T01:00:01.033334Z')).toContain('2026-10-25 02:00:01.033 +01:00')
})

for (const [length, text] of [[0, '0.000 s'], [1000, '33.333 s']] as const)
  test(`a ${length} m route preserves zero or fractional cruise duration`, async ({ page }) => {
    await setup(page, async (route, path) => {
      if (!path.endsWith('/study/route')) return false
      const result = timedResult(route.request().postDataJSON(), { ...success, length_m: length, cruise_time_s: length / 30 })
      if (length === 1000 && 'timing' in result) {
        const arrival = '2026-10-07T10:00:33.333334+02:00'
        result.timing.estimated_arrival = arrival
        result.timing.estimated_interval.mission_end = arrival
        result.timing.assessed_interval.mission_end = arrival
        result.mission.mission_end = arrival
      }
      await route.fulfill({ json: result }); return true
    })
    await routing(page).getByLabel('Departure time').fill('2026-10-07T10:00')
    if (length === 0) await routing(page).getByLabel('Destination', { exact: true }).selectOption('rheuma-podbi')
    await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
    await expect(estimate(page)).toContainText(text)
    await expect(estimate(page)).toContainText(length === 0 ? '10:00:00.000' : '10:00:33.333')
  })

test('invalid complete-interval metadata and failed routes never display an ETA', async ({ page }) => {
  let count = 0
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/route')) return false
    const response = timedResult(route.request().postDataJSON(), success)
    if ('timing' in response) response.timing.assessed_interval = { mission_start: response.timing.departure, mission_end: response.timing.departure }
    await route.fulfill({ json: count++ === 0 ? response : { ...success, status: 'duration_unstable', geometry: null, length_m: null, cruise_time_s: null } }); return true
  })
  await routing(page).getByLabel('Departure time').fill('2026-10-07T10:00')
  await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(routing(page).getByRole('alert')).toContainText('outside its assessed interval')
  await expect(estimate(page)).toContainText('Awaiting route')
  await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(routing(page).getByRole('status')).toContainText('duration_unstable')
  await expect(estimate(page)).toContainText('Awaiting route')
})

test('a delayed route cannot restore old arrival after endpoint edits', async ({ page }) => {
  let release!: () => void; const gate = new Promise<void>(resolve => { release = resolve }); let sent = false
  await setup(page, async (route, path) => { if (!path.endsWith('/study/route')) return false; sent = true; const body = route.request().postDataJSON(); await gate; await route.fulfill({ json: timedResult(body, success) }).catch(() => {}); return true })
  await routing(page).getByLabel('Departure time').fill('2026-10-07T10:00')
  await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect.poll(() => sent).toBe(true)
  await routing(page).getByLabel('Origin', { exact: true }).selectOption('mhh')
  release()
  await expect(estimate(page)).toContainText('Awaiting route')
  await expect(routing(page).getByRole('status')).toHaveCount(0)
})

test('route planning waits for in-flight preview preparation instead of overlapping it', async ({ page }) => {
  let release!: () => void; const gate = new Promise<void>(resolve => { release = resolve }); let previewStarted = false, sent = false
  await setup(page, async (route, path) => {
    if (path.endsWith('/study/layers/constraints')) { const body = route.request().postDataJSON(); if (body.duration_mode === 'automatic') { previewStarted = true; await gate }; await route.fulfill({ json: previewResult(body, layer) }); return true }
    if (path.endsWith('/study/route')) { sent = true; await route.fulfill({ json: timedResult(route.request().postDataJSON(), success) }); return true }
    return false
  })
  await routing(page).getByLabel('Departure time').fill('2026-10-07T10:00')
  await expect.poll(() => previewStarted).toBe(true)
  await routing(page).getByRole('button', { name: 'Plan regional route', exact: true }).click()
  expect(sent).toBe(false)
  release()
  await expect(estimate(page)).toContainText('10:02:00.000')
})
