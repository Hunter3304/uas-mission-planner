import { expect, test } from '@playwright/test'
import { createHash } from 'node:crypto'

test('standalone road, land use and natural costs switch independently', async ({ page }) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await page.goto('/')
  await page.getByLabel('Building cost map').check()
  for (const [category, id, cost, color, region] of [
    ['highway', 'way/2', '3', '#d77732', 'road'],
    ['landuse', 'way/3', '4', '#bd3849', 'land use'],
    ['natural', 'node/1', '2', '#78838e', 'natural feature'],
  ]) {
    await page.getByLabel('Cost category', { exact: true }).selectOption(category)
    await expect(page.getByTestId('visible-count')).toHaveText('1 / 3')
    const shape = page.locator('.leaflet-overlay-pane path.leaflet-interactive')
    await expect(shape).toHaveCount(1)
    await expect(shape).toHaveAttribute('stroke', color)
    if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
    await page.getByRole('button', { name: id, exact: true }).click()
    const details = page.getByRole('region', { name: `Selected ${region} costs` })
    await expect(details).toContainText(`cost: ${cost}`)
    await expect(details.locator('details[open] summary')).toContainText(category + '=')
  }
  await page.getByLabel('Cost category', { exact: true }).selectOption('highway')
  await page.getByLabel('Roads & paths').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('0 / 3')
  await expect(page.getByText('No analyzed road objects in the active layers.')).toBeVisible()
  await page.getByLabel('Roads & paths').check()
  await page.getByLabel('Cost category', { exact: true }).selectOption('building')
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/3', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Selected building costs' })).toContainText(
    'Building cost: 2',
  )
  await page.getByLabel('Cost category', { exact: true }).selectOption('highway')
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/2', exact: true }).click()
  await page.screenshot({ path: '../.cache/road-costs-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByLabel('Cost category', { exact: true })).toBeVisible()
  await page.screenshot({ path: '../.cache/road-costs-mobile.png', fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})

test('offline CLI sample -> real API -> map -> verified downloads', async ({ page, request }) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByTestId('total-count')).toHaveText('3')
  await expect(page.getByText('Synthetic sample objects')).toBeVisible()
  await expect(page.locator('.leaflet-overlay-pane path.leaflet-interactive')).toHaveCount(3)
  await page.getByLabel('Building cost map').check()
  await expect(page.locator('.leaflet-overlay-pane path.leaflet-interactive')).toHaveCount(1)
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/3', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Selected building costs' })).toContainText(
    'Building cost: 2',
  )
  await expect(page.getByRole('region', { name: 'Selected building costs' })).toContainText(
    'landuse=residential',
  )
  await page.getByLabel('Building cost map').uncheck()
  await page.getByLabel('Buildings').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('3 / 3')
  await page.getByLabel('Land use').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('2 / 3')
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(page.locator('.properties')).toContainText('Sample tree')
  const info = await (await request.get('/api/datasets/offline-sample')).json()
  for (const [label, format] of [
    ['Download GeoJSON', 'geojson'],
    ['GeoPackage', 'gpkg'],
    ['Metadata', 'metadata'],
  ]) {
    const event = page.waitForEvent('download')
    await page.getByRole('button', { name: new RegExp(label) }).click()
    const download = await event
    const stream = await download.createReadStream()
    const chunks = []
    for await (const chunk of stream!) chunks.push(chunk)
    const bytes = Buffer.concat(chunks)
    if (format === 'gpkg')
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(info.sha256)
    else if (format === 'geojson') expect(JSON.parse(bytes.toString()).features).toHaveLength(3)
    else expect(JSON.parse(bytes.toString()).synthetic).toBe(true)
  }
  expect(errors).toEqual([])
})

test('building costs retain tag evidence, unknowns, flags and map/table consistency', async ({
  page,
  request,
}) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await page.getByLabel('Saved dataset').selectOption('z-cost-analysis')
  await expect(page.getByTestId('total-count')).toHaveText('7')
  await expect(
    page.getByRole('region', { name: 'Building cost analysis', exact: true }),
  ).toContainText('6 buildings')
  await page.getByLabel('Building cost map').check()
  await expect(page.getByTestId('visible-count')).toHaveText('6 / 7')
  const paths = page.locator('.leaflet-overlay-pane path.leaflet-interactive')
  await expect(paths).toHaveCount(6)
  await expect(page.getByTestId('cost-summary')).toContainText('1 buildings with unknown values')
  await expect(page.getByTestId('cost-summary')).toContainText('1 without numeric cost')
  await expect(page.getByTestId('cost-summary')).toContainText('2 paper obstruction flags')
  await expect(paths.nth(0)).toHaveAttribute('fill', '#bd3849')
  await expect(paths.nth(1)).toHaveAttribute('stroke', '#202c3b')
  await expect(paths.nth(2)).toHaveAttribute('fill', '#78838e')
  await expect(paths.nth(2)).toHaveAttribute('stroke-dasharray', '5 4')
  await expect(paths.nth(3)).toHaveAttribute('fill', '#78838e')
  await expect(paths.nth(4)).toHaveAttribute('fill', '#26866c')
  await expect(paths.nth(5)).toHaveAttribute('fill', '#d4a326')
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/100', exact: true }).click()
  const details = page.getByRole('region', { name: 'Selected building costs' })
  await expect(details).toContainText('Building cost: 4')
  await details.locator('summary').filter({ hasText: 'landuse=industrial' }).click()
  await expect(details).toContainText('Table 7-1')
  await expect(details).toContainText('Cost 3')
  await expect(details).toContainText('addr:street=<img src=x onerror=alert(1)>')
  await expect(details.locator('img')).toHaveCount(0)
  await page.getByLabel('Search features').fill('unmapped_type')
  await expect(page.locator('tbody tr')).toHaveCount(1)
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/102', exact: true }).click()
  await expect(details).toContainText('Unknown / default')
  await expect(details).toContainText('Project policy v1')
  await page.getByLabel('Search features').fill('')
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/103', exact: true }).click()
  await expect(details).toContainText('No numeric cost')
  await expect(details).toContainText('Paper obstruction flag')
  await page.getByLabel('Buildings').uncheck()
  await expect(paths).toHaveCount(1) // house also has landuse
  await expect(page.getByTestId('cost-summary')).toContainText('2 paper obstruction flags')
  await page.getByLabel('Buildings').check()
  if (await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).isVisible()) await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'way/100', exact: true }).click()
  await page.screenshot({ path: '../.cache/building-costs-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: '../.cache/building-costs-mobile.png', fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  const raw = await (await request.get('/api/datasets/z-cost-analysis/features')).json()
  expect(raw.features[0].cost_analysis).toBeUndefined()
  expect(raw.features[0].properties.building).toBe('house')
  expect(errors).toEqual([])
})
