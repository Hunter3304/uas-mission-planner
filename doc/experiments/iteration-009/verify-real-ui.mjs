// Run against isolated real-data servers on ports 8012 and 5176.
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const require = createRequire(resolve(root, 'frontend/package.json'))
const { chromium, expect } = require('@playwright/test')
const output = resolve(root, process.argv[2] ?? '.cache/iteration009-ui')
await mkdir(output)
const browser = await chromium.launch({ channel: 'chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  page.setDefaultTimeout(180_000)
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('https://tile.openstreetmap.org/**', route => route.abort())
  await page.goto('http://127.0.0.1:5176')
  await expect(page.getByLabel('Saved dataset')).toBeEnabled({ timeout: 180_000 })
  await page.getByLabel('Saved dataset').selectOption('hannover-part1-v4')
  const panel = page.getByRole('region', { name: 'Regional route planning' })
  await expect(panel.getByLabel('Origin', { exact: true })).toBeEnabled({ timeout: 180_000 })
  await panel.getByLabel('Scenario start').fill('2026-10-07T10:00')
  await panel.getByLabel('Scenario end').fill('2026-10-07T10:15')
  await panel.getByLabel('Planning mode').selectOption('research')
  await panel.getByLabel('Background score assumption').fill('0')
  const started = Date.now()
  await panel.getByRole('button', { name: 'Plan regional route', exact: true }).click()
  await expect(panel.getByRole('status')).toContainText('success', { timeout: 180_000 })
  await expect(panel.getByRole('status')).toContainText('Length 3715.6 m')
  const downloadEvent = page.waitForEvent('download')
  await panel.getByRole('button', { name: 'Export displayed result' }).click()
  const download = await downloadEvent
  await download.saveAs(resolve(output, 'displayed-route.geojson'))
  const result = JSON.parse(await readFile(resolve(output, 'displayed-route.geojson'), 'utf8'))
  expect(result.features[0].geometry.coordinates[0]).toEqual([9.7967855, 52.4044919])
  expect(result.features[0].geometry.coordinates.at(-1)).toEqual([9.8044306, 52.3834796])
  expect(result.metadata.mission.mission_start).toBe('2026-10-07T10:00:00+02:00')
  expect(result.metadata.research_assumptions.length).toBeGreaterThan(0)
  expect(result.metadata.independent_validation).toBe(true)
  await page.screenshot({ path: resolve(output, 'desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: resolve(output, 'mobile.png'), fullPage: true })
  expect(errors).toEqual([])
  const evidence = { wall_ms: Date.now() - started, status: result.metadata.status,
    length_m: result.metadata.length_m, page_errors: errors, export_verified: true, mobile_verified: true }
  await writeFile(resolve(output, 'evidence.json'), JSON.stringify(evidence, null, 2))
  console.log(JSON.stringify(evidence))
} finally {
  await browser.close()
}
