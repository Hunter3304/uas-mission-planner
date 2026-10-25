import { expect, test } from '@playwright/test'
import { populationCosts } from './fixtures/populationCosts'
import { setup, osm, map, inspector, centerClick } from './fixtures/regionalSelection'

test('population class layer retries, caches visibility, clears selection and replaces native green bins', async ({ page }) => {
  let requests = 0
  const { calls, errors } = await setup(page, async (route, path) => {
    if (!path.endsWith('/study/population-costs')) return false
    requests++
    await route.fulfill(requests === 1 ? { status: 422, json: { detail: 'Population source checksum mismatch.' } } : { json: populationCosts(2, 300) })
    return true
  })
  const toggle = page.getByLabel('GHSL — population risk (250 m)', { exact: true })
  await expect(toggle).not.toBeChecked()
  expect(requests).toBe(0)
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await toggle.check()
  await expect(page.getByRole('alert').filter({ hasText: 'checksum mismatch' })).toBeVisible()
  await page.getByRole('button', { name: 'Retry population classes' }).click()
  await expect(page.getByTestId('population-cost-state')).toContainText('Ready · 1 cells')
  await centerClick(page)
  await expect(inspector(page)).toContainText('Population risk: 2 · Medium')
  await toggle.uncheck()
  await expect(inspector(page)).toContainText('Select an OSM object')
  for (let i = 0; i < 10; i++) { await toggle.check(); await toggle.uncheck() }
  await toggle.check()
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  await page.waitForTimeout(300)
  expect(requests).toBe(2)
  expect(calls.routes).toBe(0)
  expect(calls.urls.some(url => /\/study\/population(?:\?|$)/.test(url))).toBe(false)
  await expect(page.getByText('Under 25', { exact: true })).toHaveCount(0)
  expect(errors).toEqual([])
})

test('bounded display follows the viewport while preserving full-study thresholds', async ({ page }) => {
  const queries: string[] = []
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/population-costs')) return false
    const query = new URL(route.request().url()).search
    queries.push(query)
    const data = populationCosts(1, 150)
    data.display.complete = query !== ''
    data.display.matched_count = query === '' ? 20000 : 1
    await route.fulfill({ json: data })
    return true
  })
  await page.getByLabel('GHSL — population risk (250 m)', { exact: true }).check()
  await expect(page.getByTestId('population-cost-state')).toContainText('Display limited')
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  await expect.poll(() => queries.length).toBe(2)
  expect(queries[1]).toContain('bbox=')
  await expect(page.getByTestId('population-cost-state')).not.toContainText('Display limited')
  await page.getByText('Population class thresholds', { exact: true }).click()
  await expect(page.getByTestId('population-cost-state')).toContainText('Maximum study density: 10,000 people/km²')
})

test('initial map movement and hide/show preserve a slow first preparation', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let requests = 0
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/population-costs')) return false
    requests++
    await gate
    await route.fulfill({ json: populationCosts() })
    return true
  })
  const toggle = page.getByLabel('GHSL — population risk (250 m)', { exact: true })
  await toggle.check()
  await expect.poll(() => requests).toBe(1)
  await page.getByRole('button', { name: 'Focus origin', exact: true }).click()
  await toggle.uncheck()
  await toggle.check()
  await page.waitForTimeout(350)
  expect(requests).toBe(1)
  release()
  await expect(page.getByTestId('population-cost-state')).toContainText('Ready · 1 cells')
  expect(requests).toBe(1)
})

test('five colored risk classes and gray NoData render together on desktop and mobile', async ({ page }, info) => {
  await setup(page, async (route, path) => {
    if (!path.endsWith('/study/population-costs')) return false
    const data = populationCosts()
    data.display.returned_count = data.display.matched_count = 6
    data.layer.features = Array.from({ length: 6 }, (_, i) => {
      const score = i === 5 ? null : i
      const feature = populationCosts(score, i * 100).layer.features[0]
      feature.id = `population250:0:${i}`
      const x = 9.792 + (i % 3) * .005, y = 52.380 + Math.floor(i / 3) * .008
      feature.geometry.coordinates = [[[x, y], [x + .005, y], [x + .005, y + .008], [x, y + .008], [x, y]]]
      return feature
    })
    await route.fulfill({ json: data })
    return true
  })
  await osm(page).getByLabel('Show saved OSM').uncheck()
  await page.getByLabel('Street basemap — online OpenStreetMap tiles', { exact: true }).uncheck()
  await page.getByLabel('GHSL — population risk (250 m)', { exact: true }).check()
  await expect(page.getByTestId('population-cost-state')).toContainText('Ready · 6 cells')
  await expect(page.getByLabel('Population risk legend').locator('span')).toHaveCount(6)
  await page.screenshot({ path: info.outputPath('population-classes-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await map(page).scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('population-classes-mobile.png'), fullPage: true })
})
