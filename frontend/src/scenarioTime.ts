/** Convert an unambiguous Berlin wall time without using the host's time zone. */
export function berlinTimestamp(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(value))
    throw new Error('Select a complete scenario date and time.')
  const wall = value.length === 16 ? `${value}:00` : value
  const format = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })
  const candidates = ['+01:00', '+02:00'].filter(offset => {
    const date = new Date(wall + offset)
    return !Number.isNaN(date.getTime()) && format.format(date).replace(' ', 'T') === wall
  })
  if (candidates.length !== 1)
    throw new Error('This Berlin time is missing or ambiguous during a daylight-saving transition. Select another time.')
  return wall + candidates[0]
}

export function scenarioInterval(start: string, end: string) {
  const mission_start = berlinTimestamp(start)
  const mission_end = berlinTimestamp(end)
  const duration = Date.parse(mission_end) - Date.parse(mission_start)
  if (duration <= 0 || duration > 86_400_000)
    throw new Error('Scenario end must be after start and within 24 hours.')
  return { mission_start, mission_end }
}

export interface FlightInterval { mission_start: string; mission_end: string }
export interface FlightTiming {
  mode: 'automatic'
  departure?: string
  estimated_arrival: string | null
  cruise_time_s: number | null
  estimated_interval: FlightInterval | null
  assessed_interval: FlightInterval
  cruise_only: boolean
}

export function berlinDisplay(value: string) {
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return 'Unavailable'
  const parts = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3, timeZoneName: 'longOffset', hourCycle: 'h23' }).formatToParts(date)
  const get = (key: string) => parts.find(part => part.type === key)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}:${get('second')}.${get('fractionalSecond')} ${get('timeZoneName').replace('GMT', '')} (Europe/Berlin)`
}

export function checkFlightTiming(timing: FlightTiming | undefined, departure: string, length: number | null, speed: number) {
  if (!timing || timing.mode !== 'automatic' || !timing.cruise_only || timing.departure !== departure || length == null || !Number.isFinite(length) || length < 0 || !Number.isFinite(speed) || speed < 25 || speed > 35 || typeof timing.cruise_time_s !== 'number' || !Number.isFinite(timing.cruise_time_s) || !timing.estimated_arrival || !timing.estimated_interval || !timing.assessed_interval)
    throw new Error('The data service returned an invalid automatic flight interval. Refresh and plan again.')
  const start = Date.parse(departure), end = Date.parse(timing.estimated_arrival)
  const duration = length / speed
  if (!Number.isFinite(end) || !Number.isFinite(start) || timing.cruise_time_s == null || Math.abs(timing.cruise_time_s - duration) > 0.000001 || Math.abs(end - start - duration * 1000) > 1.01 || Date.parse(timing.estimated_interval.mission_start) !== start || Date.parse(timing.estimated_interval.mission_end) !== end || !(Date.parse(timing.assessed_interval.mission_start) <= start && Date.parse(timing.assessed_interval.mission_end) >= end))
    throw new Error('The returned route time is outside its assessed interval or does not match its length and speed.')
}
