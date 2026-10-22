import { useEffect, useRef, useState } from 'react'
import { postJson } from './api'
import type { ConstraintLayers } from './RegionalMap'

/** One retained scenario, one preparation in flight, independent of visibility. */
export default function useScenarioLayers(datasetId: string, requestKey: string, enabled: boolean) {
  const [state, setState] = useState<{
    key: string
    data?: ConstraintLayers
    error?: string
    loading?: boolean
  }>({ key: '' })
  const [attempt, setAttempt] = useState(0)
  const cached = useRef<{ key: string; data: ConstraintLayers } | null>(null)
  const running = useRef<Promise<void> | null>(null)
  const controller = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; controller.current?.abort() }
  }, [])
  useEffect(() => {
    if (!requestKey || !enabled) return
    let obsolete = false
    const timer = setTimeout(async () => {
      // Await old preparation instead of aborting only its HTTP consumer and
      // submitting another expensive job that the backend cannot yet cancel.
      if (running.current) await running.current
      if (obsolete || !mounted.current) return
      if (cached.current?.key === requestKey) {
        setState({ key: requestKey, data: cached.current.data })
        return
      }
      const active = new AbortController()
      controller.current = active
      setState({ key: requestKey, loading: true })
      const task = (async () => {
        try {
          const data = await postJson<ConstraintLayers>(
            `/api/datasets/${encodeURIComponent(datasetId)}/study/layers/constraints`,
            JSON.parse(requestKey), active.signal,
          )
          if (!Array.isArray(data.blocked?.features) || !Array.isArray(data.unknown?.features) || !Array.isArray(data.diagnostics))
            throw new Error('The scenario layer response is invalid. Retry to load it again.')
          if (mounted.current && !active.signal.aborted) {
            // Save even if the user hid every layer while this request ran.
            cached.current = { key: requestKey, data }
            setState({ key: requestKey, data })
          }
        } catch (failure) {
          if (mounted.current && !active.signal.aborted)
            setState({ key: requestKey, error: failure instanceof Error ? failure.message : 'Cannot load scenario layers.' })
        }
      })()
      running.current = task
      await task
      if (running.current === task) running.current = null
    }, 300)
    return () => { obsolete = true; clearTimeout(timer) }
  }, [datasetId, requestKey, enabled, attempt])
  const current = state.key === requestKey ? state : null
  return {
    data: current?.data ?? null,
    error: current?.error ?? '',
    loading: enabled && !!requestKey && (!current || !!current.loading),
    retry: () => { cached.current = null; setAttempt(value => value + 1) },
  }
}
