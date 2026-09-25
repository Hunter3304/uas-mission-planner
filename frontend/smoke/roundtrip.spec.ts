import { expect, test } from '@playwright/test'
import { createHash } from 'node:crypto'

test('offline CLI sample -> real API -> map -> verified downloads', async ({ page, request }) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByTestId('total-count')).toHaveText('3')
  await expect(page.getByText('Synthetic sample objects')).toBeVisible()
  await expect(page.locator('.leaflet-overlay-pane path.leaflet-interactive')).toHaveCount(3)
  await page.getByLabel('Buildings').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('3 / 3')
  await page.getByLabel('Land use').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('2 / 3')
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
