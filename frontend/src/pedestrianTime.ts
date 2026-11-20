export const pedestrianWindows = [
  ['05-08', '05:00–08:00'],
  ['08-10', '08:00–10:00'],
  ['10-13', '10:00–13:00'],
  ['13-16', '13:00–16:00'],
  ['16-19', '16:00–19:00'],
  ['19-22', '19:00–22:00'],
  ['22-05', '22:00–05:00 (next day)'],
] as const

export type PedestrianWindowId = typeof pedestrianWindows[number][0]
export type PedestrianWindow = { id: PedestrianWindowId; label: string; timezone: string }

const berlinHour = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Berlin', hour: '2-digit', hourCycle: 'h23' })

export function pedestrianWindow(timestamp: string): PedestrianWindowId {
  const hour = Number(berlinHour.format(new Date(timestamp)))
  const window = pedestrianWindows.find(([id]) => {
    const [start, end] = id.split('-').map(Number)
    return start < end ? hour >= start && hour < end : hour >= start || hour < end
  })
  if (!window) throw new Error('Choose a valid Berlin departure time.')
  return window[0]
}
