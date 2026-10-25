interface Request { scenario: { mission_start: string; mission_end?: string; speed_m_s: number } }

export function timedResult<T extends { status: string; length_m: number | null }>(request: Request, result: T) {
  if (result.status !== 'success' || result.length_m == null) return result
  const departure = request.scenario.mission_start
  const duration = result.length_m / request.scenario.speed_m_s
  const arrival = new Date(Date.parse(departure) + Math.ceil(duration * 1000)).toISOString()
  const interval = { mission_start: departure, mission_end: arrival }
  return { ...result, mission: { ...request.scenario, ...interval }, timing: { mode: 'automatic', departure, estimated_arrival: arrival, estimated_interval: interval, assessed_interval: interval, cruise_time_s: duration, cruise_only: true } }
}

export function previewResult<T>(request: Request, result: T) {
  const interval = { mission_start: request.scenario.mission_start, mission_end: request.scenario.mission_end ?? new Date(Date.parse(request.scenario.mission_start) + 60_000).toISOString() }
  return { ...result, flight_interval: { mode: 'provisional', assessed_interval: interval, interpretation: 'Synthetic provisional preview, not an ETA.' } }
}
