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
