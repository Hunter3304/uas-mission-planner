
import { expect, test } from '@playwright/test'
import { bounds, centerClick, empty, geometry, inspector, osm, setup } from './fixtures/regionalSelection'

test('outdoor pedestrian layer shows the public estimate, shared scale and coverage states', async ({ page }) => {
  const requests: string[] = []
  const { calls, errors } = await setup(page, async (route, path) => {
    if (path.endsWith('/study')) {
      await route.fulfill({ json: { region_id: 'hannover-lehrte-5km', config: { bounds, locations: [{ id: 'rheuma-podbi', name: 'Origin', longitude: 9.8, latitude: 52.388 }, { id: 'mhh', name: 'Destination', longitude: 9.805, latitude: 52.388 }] }, sources: {} } })
      return true
    }
    if (!path.endsWith('/study/pedestrian-exposure')) return false
    const scenario = new URL(route.request().url()).searchParams.get('scenario')
    if (!scenario) throw new Error('Expected a scenario')
    requests.push(scenario)
    const label = { '08-10': '08:00–10:00', '13-16': '13:00–16:00', '19-22': '19:00–22:00', '22-05': '22:00–05:00 (next day)' }[scenario]
    const window = { id: scenario, label, timezone: 'Europe/Berlin' }
    const common = { window, identity: scenario, input_kind: 'mid-public', display_max_people: 10 }
    const count = scenario === '19-22' ? null : scenario === '08-10' ? 6 : 0
    await route.fulfill({ json: scenario === '22-05'
      ? { ...common, state: 'unavailable', reason: 'No prepared pedestrian layer for this study.', layer: empty }
      : { ...common, state: 'ready', layer: { ...empty, features: [{ type: 'Feature', id: 'population150:0:0', geometry, properties: {
        mean_people: count, area_m2: 22500, people_per_km2: count === null ? null : count / 0.0225,
        state: count === null ? 'unavailable' : 'known', coverage_reason: count === null ? 'ghsl_coverage' : null,
      } }] } },
    })
    return true
  })

  const outdoors = page.getByRole('region', { name: 'Outdoor pedestrians', exact: true })
  const dipul = page.getByRole('region', { name: 'DIPUL restrictions', exact: true })
  const desktop = page.viewportSize()!
  await expect.poll(async () => {
    const [left, right] = await Promise.all([outdoors.boundingBox(), dipul.boundingBox()])
    return left != null && right != null && left.y === right.y && left.x < right.x && left.width === right.width
  }).toBe(true)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(async () => {
    const [top, bottom] = await Promise.all([outdoors.boundingBox(), dipul.boundingBox()])
    return top != null && bottom != null && top.x === bottom.x && top.y + top.height < bottom.y
  }).toBe(true)
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.setViewportSize(desktop)
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await expect(page.getByLabel('Show outdoor pedestrian estimates')).not.toBeChecked()
  expect(requests).toEqual([])
  await page.getByLabel('Show outdoor pedestrian estimates').check()
  const legend = page.getByLabel('Outdoor pedestrian legend')
  await expect(legend).toContainText('Up to 10')
  await expect(page.getByText(/MiD 2023 municipal estimates/)).toBeVisible()
  await centerClick(page)
  await expect(inspector(page)).toContainText('6 average pedestrians')
  await expect(inspector(page)).toContainText('08:00–10:00 · Europe/Berlin')

  const scenario = page.getByLabel('Pedestrian time window')
  await expect(scenario.locator('option')).toHaveCount(7)
  await scenario.selectOption('13-16')
  await expect(inspector(page)).not.toContainText('6 average pedestrians')
  await expect(legend).toContainText('Up to 10')
  await centerClick(page)
  await expect(inspector(page)).toContainText('0 average pedestrians')

  await scenario.selectOption('19-22')
  await expect(legend).toBeVisible()
  await centerClick(page)
  await expect(inspector(page)).toContainText('Incomplete population grid coverage')

  await scenario.selectOption('22-05')
  await expect(page.getByText('No prepared pedestrian layer for this study.')).toBeVisible()
  await expect(legend).toHaveCount(0)
  await expect(inspector(page)).toContainText('Select an OSM object')
  expect(requests).toEqual(['08-10', '13-16', '19-22', '22-05'])
  expect(calls.routes).toBe(0)
  expect(errors).toEqual([])
})

test('Hannover opens in weighted pedestrian mode with exact endpoints and a configurable native budget', async ({ page }) => {
  const requests: { objective: string; algorithm: string; scenario: { mission_start: string }; background_cost?: number }[] = []
  const locations = [
    { id: 'rheuma-podbi', name: 'Origin', longitude: 9.8, latitude: 52.388 },
    { id: 'mhh', name: 'Destination', longitude: 9.805, latitude: 52.388 },
    ...Array.from({ length: 6 }, (_, i) => ({ id: 'site-' + i, name: 'Site ' + i, longitude: 9.8, latitude: 52.39 + i / 1000 })),
  ]
  const early = { id: '10-13', label: '10:00–13:00', timezone: 'Europe/Berlin' }
  const late = { id: '13-16', label: '13:00–16:00', timezone: 'Europe/Berlin' }
  const { errors } = await setup(page, async (route, path) => {
    if (path === '/api/datasets') {
      await route.fulfill({ json: { datasets: [{ id: 'another-dataset' }, { id: 'hannover-part1-v4' }] } })
      return true
    }
    if (path.endsWith('/study')) {
      await route.fulfill({ json: { region_id: 'hannover-lehrte-5km', config: { bounds, locations }, sources: {} } })
      return true
    }
    if (path.endsWith('/study/pedestrian-exposure')) {
      const window = new URL(route.request().url()).searchParams.get('scenario') === early.id ? early : late
      await route.fulfill({ json: { state: 'ready', window, identity: `fixture:${window.id}`, display_max_people: 1, layer: empty } })
      return true
    }
    if (!path.endsWith('/study/route')) return false
    const request = route.request().postDataJSON()
    requests.push(request)
    if (request.time_budget_s === 30) {
      await route.fulfill({ json: { status: 'planner_unavailable', length_m: null, preparation_ms: 15, planner_ms: 0 } })
      return true
    }
    const departure = request.scenario.mission_start
    const arrival = '2026-10-07T13:00:01+02:00'
    const interval = { mission_start: departure, mission_end: arrival }
    await route.fulfill({ json: {
      status: 'success', geometry: { type: 'LineString', coordinates: [request.start_coordinate, request.end_coordinate] },
      length_m: 60, objective_cost: 30, pedestrian_exposure_m: 20,
      effective_weights: { distance: request.distance_weight, pedestrian_exposure: request.exposure_weight },
      pedestrian_exposure: { assessment: 'assessed', window: early, model_version: 'fixture-v1', layer_identity: 'fixture:10-13', crosses_window: true, arrival_window: late },
      preparation_ms: 15, planner_ms: 10, mission: interval, endpoint_diagnostics: {}, research_assumptions: [],
      timing: { mode: 'automatic', departure, estimated_arrival: arrival, cruise_time_s: 2, assessed_interval: interval, estimated_interval: interval, cruise_only: true },
    } })
    return true
  })
  const mode = page.getByRole('combobox', { name: 'Routing mode', exact: true })
  const algorithm = page.getByRole('combobox', { name: 'Algorithm', exact: true })
  const budget = page.getByLabel('Search budget (s)', { exact: true })
  const objective = page.getByLabel('Objective', { exact: true })
  const method = page.getByLabel('Selection method')
  const distance = page.getByLabel('Distance weight', { exact: true })
  const exposure = page.getByLabel('Exposure weight', { exact: true })
  await expect(page.getByLabel('Saved dataset', { exact: true })).toHaveValue('hannover-part1-v4')
  await expect(mode).toHaveValue('pedestrian')
  await expect(algorithm).toHaveValue('abitstar')
  await expect(algorithm.locator('option')).toHaveText(['A*', 'Dijkstra', 'ABIT*'])
  await expect(budget).toHaveValue('30')
  await expect(budget).toHaveAttribute('max', '120')
  await expect(distance).toHaveValue('0.1')
  await expect(exposure).toHaveValue('0.9')
  await expect(method).toHaveValue('sites')
  await expect(page.getByLabel('Origin', { exact: true }).locator('option')).toHaveCount(8)
  await expect(page.getByLabel('Destination', { exact: true }).locator('option')).toHaveCount(8)
  await mode.selectOption('existing')
  await objective.selectOption('distance')
  await page.getByLabel('Include population').check()
  await page.getByLabel('Population weight', { exact: true }).fill('2')
  await mode.selectOption('pedestrian')
  await expect(objective).toHaveCount(0)
  await expect(page.getByLabel('Population weight', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Grid spacing (m)', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Altitude AGL (m)', { exact: true })).toBeVisible()
  await page.getByLabel('Departure time', { exact: true }).fill('2026-10-07T12:59:59')
  await expect(page.getByText('Departure window 10:00–13:00', { exact: true })).toBeVisible()
  const plan = page.getByRole('button', { name: 'Plan regional route' })
  await plan.click()
  await expect(page.getByText(/ABIT\* requires native OMPL/)).toBeVisible()
  expect(requests[0]).toMatchObject({ objective: 'pedestrian_exposure', algorithm: 'abitstar', time_budget_s: 30, distance_weight: 0.1, exposure_weight: 0.9 })
  await algorithm.selectOption('dijkstra')
  await expect(budget).toHaveCount(0)
  await algorithm.selectOption('abitstar')
  await budget.fill('120')
  await distance.fill('0.25')
  await exposure.fill('0.75')
  await method.selectOption('coordinates')
  const startLongitude = page.getByLabel('Start longitude')
  await startLongitude.fill('9.85')
  await expect(page.locator('#start_lon-error')).toBeVisible()
  await plan.click()
  expect(requests).toHaveLength(1)
  for (const [label, value] of [['Start longitude', '9.80001'], ['Start latitude', '52.388'], ['End longitude', '9.805'], ['End latitude', '52.38802']])
    await page.getByLabel(label).fill(value)
  await plan.click()
  await expect(page.getByText('Pedestrian exposure E 20.00 m')).toBeVisible()
  await expect(page.getByText(/Arrival falls in 13:00–16:00/)).toBeVisible()
  await expect(page.getByText('Effective weights: distance 0.25 · exposure 0.75')).toBeVisible()
  expect(requests).toHaveLength(2)
  const start = [9.80001, 52.388], end = [9.805, 52.38802]
  expect(requests[1]).toMatchObject({ objective: 'pedestrian_exposure', algorithm: 'abitstar', start_coordinate: start, end_coordinate: end, time_budget_s: 120, distance_weight: 0.25, exposure_weight: 0.75 })
  expect(requests[1].background_cost).toBeUndefined()
  const downloaded = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export displayed result' }).click()
  const stream = await (await downloaded).createReadStream()
  let text = ''
  for await (const chunk of stream!) text += chunk.toString()
  expect(JSON.parse(text).features[0]).toMatchObject({ geometry: { coordinates: [start, end] }, properties: { effective_weights: { distance: 0.25, pedestrian_exposure: 0.75 } } })
  await method.selectOption('sites')
  await expect(page.getByRole('button', { name: 'Export displayed result' })).toHaveCount(0)
  await page.getByLabel('Departure time', { exact: true }).fill('2026-10-07T13:00')
  await expect(page.getByText('Departure window 13:00–16:00', { exact: true })).toBeVisible()
  await expect(page.getByText('Pedestrian exposure E 20.00 m')).toHaveCount(0)
  await mode.selectOption('existing')
  await expect(objective).toHaveValue('distance')
  await expect(page.getByLabel('Population weight', { exact: true })).toHaveValue('2')
  expect(errors).toEqual([])
})
