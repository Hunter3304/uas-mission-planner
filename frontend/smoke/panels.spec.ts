import { expect, test } from '@playwright/test'

test('feature panels remain available, auto-open for selections and collapse independently', async ({
  page,
}) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await page.goto('/')
  const browser = page.getByRole('region', { name: 'Feature browser', exact: true })
  const details = page.getByRole('region', { name: 'Feature details', exact: true })
  await expect(browser).toBeVisible()
  await expect(details).toBeVisible()
  await expect(page.getByLabel('Search features')).toBeHidden()
  await page.getByRole('button', { name: 'Expand Feature details', exact: true }).click()
  await expect(details).toContainText('Select a feature on the map')
  await page.getByRole('button', { name: 'Expand Feature browser', exact: true }).click()
  await page.getByRole('button', { name: 'node/1', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'Collapse Feature details', exact: true }),
  ).toHaveAttribute('aria-expanded', 'true')
  await expect(details.locator('.properties')).toContainText('Sample tree')
  await page.getByRole('button', { name: 'Collapse Feature browser', exact: true }).click()
  await expect(page.getByLabel('Search features')).toBeHidden()
  await expect(details.locator('.properties')).toBeVisible()
  await page.getByRole('button', { name: 'Collapse Feature details', exact: true }).click()
  await expect(details.locator('.properties')).toBeHidden()
  await page.getByRole('button', { name: 'Expand Feature details', exact: true }).click()
  await expect(details.locator('.properties')).toContainText('Sample tree')
  await details.getByRole('button', { name: 'Clear', exact: true }).click()
  await expect(
    page.getByRole('button', { name: 'Expand Feature browser', exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Expand Feature details', exact: true }),
  ).toBeVisible()
  await expect(page.getByRole('region', { name: 'Dataset map' })).toBeVisible()
})

test('main panels fold without hiding the map or losing planner inputs and results', async ({
  page,
}) => {
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await page.goto('/')
  await page.getByLabel('Saved dataset').selectOption('z-risk-demo')
  const map = page.getByRole('region', { name: 'Dataset map' })
  await page.getByRole('button', { name: 'Collapse Building cost analysis', exact: true }).click()
  await expect(page.getByLabel('Building cost map')).toBeHidden()
  await page
    .getByRole('button', { name: 'Collapse Independent source layers', exact: true })
    .click()
  await expect(page.getByLabel('Grid cell (m)', { exact: true })).toBeHidden()
  await expect(page.getByRole('combobox', { name: 'Objective', exact: true })).toBeVisible()
  await page
    .getByRole('button', { name: 'Collapse Location and source inspection', exact: true })
    .click()
  await expect(map).toBeVisible()
  const objective = page.getByRole('combobox', { name: 'Objective', exact: true })
  await expect(page.getByLabel('Risk weight', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Distance weight', { exact: true })).toHaveCount(0)
  await expect(page.getByLabel('Background score assumption')).toHaveCount(0)
  await expect(page.getByLabel('Safety distance (m)')).toBeVisible()
  await expect(page.getByLabel('ABIT* budget (s)')).toBeVisible()
  await objective.selectOption('risk')
  await page.getByLabel('Risk weight', { exact: true }).fill('0.7')
  await page.getByLabel('Background score assumption').fill('0')
  await objective.selectOption('distance')
  await expect(page.getByLabel('Risk weight', { exact: true })).toHaveCount(0)
  await objective.selectOption('risk')
  await expect(page.getByLabel('Risk weight', { exact: true })).toHaveValue('0.7')
  await expect(page.getByLabel('Background score assumption')).toHaveValue('0')
  const generate = page.getByRole('button', { name: 'Generate route', exact: true })
  await expect(generate).toBeEnabled({ timeout: 15000 })
  await generate.click()
  await expect(page.getByTestId('route-result')).toContainText('Route found')
  await page.getByRole('button', { name: 'Collapse Route planning', exact: true }).click()
  await expect(generate).toBeHidden()
  await expect(map).toBeVisible()
  await page.getByRole('button', { name: 'Expand Route planning', exact: true }).click()
  await expect(page.getByTestId('route-result')).toContainText('Route found')
  await expect(page.getByLabel('Risk weight', { exact: true })).toHaveValue('0.7')
  await page.setViewportSize({ width: 390, height: 844 })
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    .toBe(true)
  await page.screenshot({ path: '../.cache/ui-panels-mobile.png', fullPage: true })
})
