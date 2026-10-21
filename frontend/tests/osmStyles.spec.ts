import { expect, test } from '@playwright/test'
import { categoryColor, costColor, osmStyle } from '../src/osmStyles'

const visible = { building: true, highway: true, landuse: true, natural: true }

test('overlapping category precedence matches the demo and follows visibility', () => {
  const memberships = ['natural', 'landuse', 'highway', 'building'] as const
  expect(categoryColor(memberships, visible)).toBe('#bc784a')
  expect(categoryColor(memberships, { ...visible, building: false })).toBe('#657ac0')
  expect(categoryColor(memberships, { ...visible, building: false, highway: false })).toBe('#b7983c')
  expect(categoryColor(['natural'], visible)).toBe('#26877a')
})

test('known costs, provisional mixed costs and costless/excluded scores retain demo colors', () => {
  const score = { cost: 0, status: 'matched', has_default: false, obstruction: false }
  expect([0, 1, 2, 3, 4].map(cost => costColor({ ...score, cost })))
    .toEqual(['#26866c', '#80a944', '#d4a326', '#d77732', '#bd3849'])
  expect(costColor({ ...score, cost: 4, has_default: true, status: 'default' })).toBe('#78838e')
  expect(costColor({ ...score, cost: null, status: 'excluded' })).toBe('#78838e')
  expect(costColor(null)).toBe('#78838e')
})

test('selected category score alone controls cost outlines, gray dashes and fill', () => {
  const style = osmStyle(['building', 'landuse'], visible, true,
    { cost: null, status: 'obstruction_only', has_default: false, obstruction: true })
  expect(style).toMatchObject({ color: '#202c3b', fillColor: '#78838e', dashArray: '5 4', weight: 4 })
  expect(osmStyle(['building', 'landuse'], visible, true,
    { cost: 1, status: 'matched', has_default: false, obstruction: false }))
    .toMatchObject({ color: '#80a944', fillColor: '#80a944', weight: 3, dashArray: undefined })
  expect(osmStyle(['building', 'landuse'], visible, false)).toMatchObject({
    color: '#bc784a', fillOpacity: 0.25, dashArray: undefined,
  })
})
