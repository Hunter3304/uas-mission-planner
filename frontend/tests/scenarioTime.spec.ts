import { expect, test } from '@playwright/test'
import { berlinTimestamp, scenarioInterval } from '../src/scenarioTime'

test('Berlin wall time handles both offsets and rejects impossible or ambiguous dates', () => {
  expect(berlinTimestamp('2026-10-08T10:00')).toBe('2026-10-08T10:00:00+02:00')
  expect(berlinTimestamp('2026-12-08T10:00')).toBe('2026-12-08T10:00:00+01:00')
  expect(() => berlinTimestamp('2026-03-29T02:30')).toThrow(/transition/)
  expect(() => berlinTimestamp('2026-10-25T02:30')).toThrow(/transition/)
  expect(() => berlinTimestamp('2026-02-30T10:00')).toThrow()
  expect(() => scenarioInterval('2026-10-08T10:00', '2026-10-08T09:00')).toThrow(/after/)
  expect(() => scenarioInterval('2026-10-08T10:00', '2026-10-09T10:01')).toThrow(/24 hours/)
})
