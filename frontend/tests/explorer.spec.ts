import { expect, test, type Page } from '@playwright/test'

const unsafeName = '<img src=x onerror=alert(1)>'
const features = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [10.52, 52.27] },
      properties: { element_type: 'node', osm_id: 1, natural: 'tree', name: unsafeName },
    },
    {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [10.519, 52.269],
          [10.521, 52.271],
        ],
      },
      properties: {
        element_type: 'way',
        osm_id: 2,
        highway: 'path',
        landuse: 'recreation_ground',
        name: 'Shared path',
      },
    },
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [10.52, 52.269],
            [10.521, 52.269],
            [10.521, 52.27],
            [10.52, 52.269],
          ],
        ],
      },
      properties: { element_type: 'way', osm_id: 3, building: 'yes' },
    },
  ],
}
const dataset = {
  id: 'demo',
  verified: true,
  feature_count: 3,
  crs: 'EPSG:4326',
  geometry_counts: { Point: 1, LineString: 1, Polygon: 1 },
  layer_counts: { natural: 1, highway: 1, landuse: 1, building: 1 },
  query_bounds: { west: 10.519, south: 52.269, east: 10.521, north: 52.271 },
  feature_bounds: [10.519, 52.269, 10.521, 52.271],
  query_area_km2: 0.03,
  saved_at_utc: '2026-09-25T10:00:00Z',
  invalid_geometry_count: 0,
}
async function mock(page: Page, mode = 'normal') {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await page.route('**/api/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (mode === 'error')
      return route.fulfill({ status: 503, json: { detail: 'Service unavailable' } })
    if (path === '/api/datasets')
      return route.fulfill({ json: { datasets: mode === 'missing' ? [] : [dataset] } })
    if (mode === 'corrupt')
      return route.fulfill({
        status: 422,
        json: { detail: 'Dataset integrity verification failed.' },
      })
    if (path.endsWith('/download/gpkg'))
      return route.fulfill({
        contentType: 'application/geopackage+sqlite3',
        body: JSON.stringify(features),
      })
    if (path.endsWith('/features') || path.includes('/download/'))
      return route.fulfill({ json: mode === 'empty' ? { ...features, features: [] } : features })
    return route.fulfill({
      json:
        mode === 'empty'
          ? {
              ...dataset,
              feature_count: 0,
              feature_bounds: null,
              layer_counts: {},
              geometry_counts: {},
            }
          : dataset,
    })
  })
}

test('layers use union counts, features remain usable without basemap, tags are safe', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await mock(page)
  await page.goto('/')
  await expect(page.getByTestId('total-count')).toHaveText('3')
  await expect(page.locator('.leaflet-overlay-pane path.leaflet-interactive')).toHaveCount(3)
  await page.getByLabel('Roads & paths').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('3 / 3')
  await page.getByLabel('Land use', { exact: false }).uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('2 / 3')
  await page.getByLabel('Buildings').uncheck()
  await page.getByLabel('Natural features').uncheck()
  await expect(page.getByTestId('visible-count')).toHaveText('0 / 3')
  await expect(page.locator('.leaflet-overlay-pane path.leaflet-interactive')).toHaveCount(0)
  await page.getByLabel('Natural features').check()
  await page.getByLabel('Search features').fill('node/1')
  await page.getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(page.locator('.properties')).toContainText(unsafeName)
  await expect(page.locator('.properties img')).toHaveCount(0)
  await expect(
    page.getByText('Basemap unavailable. Your saved data is still visible.'),
  ).toBeVisible()
  expect(errors).toEqual([])
})

test('downloads are complete even when a layer is hidden; mobile fits viewport', async ({
  page,
}) => {
  await mock(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByLabel('Buildings').uncheck()
  for (const [name, filename] of [
    ['Download GeoJSON', 'demo.geojson'],
    ['GeoPackage', 'demo.gpkg'],
    ['Metadata', 'demo.metadata.json'],
  ]) {
    const event = page.waitForEvent('download')
    await page.getByRole('button', { name: new RegExp(name) }).click()
    const download = await event
    expect(download.suggestedFilename()).toBe(filename)
    const stream = await download.createReadStream()
    const chunks = []
    for await (const chunk of stream!) chunks.push(chunk)
    expect(JSON.parse(Buffer.concat(chunks).toString()).features).toHaveLength(3)
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})

for (const [mode, message] of [
  ['missing', 'Your workspace is ready for data'],
  ['empty', 'No matching features in this dataset.'],
  ['corrupt', 'Dataset integrity verification failed.'],
  ['error', 'Service unavailable'],
]) {
  test(`handles ${mode} data`, async ({ page }) => {
    await mock(page, mode)
    await page.goto('/')
    await expect(page.getByText(message, { exact: false })).toBeVisible()
    if (mode === 'error') {
      await page.unroute('**/api/**')
      await mock(page)
      await page.getByRole('button', { name: 'Try again' }).click()
      await expect(page.getByTestId('total-count')).toHaveText('3')
    }
  })
}

for (const mode of ['network', 'html']) {
  test(`actionable ${mode} response with retry`, async ({ page }) => {
    await page.route('**/api/**', (route) =>
      mode === 'network'
        ? route.abort()
        : route.fulfill({
            contentType: 'text/html',
            body: '<!doctype html><html>Wrong server</html>',
          }),
    )
    await page.goto('/')
    await expect(page.getByRole('alert')).toContainText(
      mode === 'network' ? 'Start the backend on port 8000' : 'Restart the frontend and backend',
    )
    await page.unroute('**/api/**')
    await mock(page)
    await page.getByRole('button', { name: 'Try again' }).click()
    await expect(page.getByTestId('total-count')).toHaveText('3')
  })
}

test('failed or HTML download is reported and does not download a bogus file', async ({ page }) => {
  await mock(page)
  await page.goto('/')
  await expect(page.getByTestId('total-count')).toHaveText('3')
  let downloads = 0
  page.on('download', () => downloads++)
  await page.route('**/download/**', (route) =>
    route.fulfill({ status: 422, json: { detail: 'Dataset cannot be verified.' } }),
  )
  await page.getByRole('button', { name: /Download GeoJSON/ }).click()
  await expect(page.locator('.download-status')).toHaveText('Dataset cannot be verified.')
  await page.unroute('**/download/**')
  await page.route('**/download/**', (route) =>
    route.fulfill({ contentType: 'text/html', body: '<html>Wrong server</html>' }),
  )
  await page.getByRole('button', { name: /Download GeoJSON/ }).click()
  await expect(page.locator('.download-status')).toContainText('unexpected file type')
  expect(downloads).toBe(0)
  await expect(page.getByRole('button', { name: /Download GeoJSON/ })).toBeEnabled()
})
