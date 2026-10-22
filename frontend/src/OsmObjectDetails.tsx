import { useEffect, useState } from 'react'
import { getJson } from './api'
import { CostDetails, showValue } from './BuildingCosts'
import { layers, type OsmObjectDetail } from './types'
import { snapshotKey, useMapSelection } from './mapSelection'

export default function OsmObjectDetails({
  base,
  selection,
}: {
  base: string
  selection: { key: string; snapshot: string }
}) {
  const { invalidate } = useMapSelection()
  const [detail, setDetail] = useState<OsmObjectDetail | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const active = new AbortController()
    setDetail(null)
    setError('')
    getJson<OsmObjectDetail>(`${base}/features/${selection.key}`, active.signal)
      .then((value) => {
        if (active.signal.aborted) return
        if (snapshotKey(value.display.identity) !== selection.snapshot) {
          invalidate('osm', selection.key, selection.snapshot, 'The source changed. Refresh OSM before selecting this object again.')
          return
        }
        if (`${value.properties.element_type}/${value.properties.osm_id}` !== selection.key)
          throw new Error('The returned details do not match the selected object. Retry to load its original data.')
        setDetail(value)
      })
      .catch((failure) => {
        if (!active.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'Cannot load object details.')
      })
    return () => active.abort()
  }, [base, selection.key, selection.snapshot, attempt, invalidate])
  return (
    <section className="osm-details" aria-label="Selected OSM object">
      <h3>OSM {selection.key}</h3>
      {!detail && !error && <p role="status">Loading original object details…</p>}
      {error && (
        <>
          <p role="alert">{error}</p>
          <button type="button" onClick={() => setAttempt((value) => value + 1)}>
            Retry object details
          </button>
        </>
      )}
      {detail && (
        <>
          <p>
            Original source tags and geometry; categories:{' '}
            {detail.display.categories.join(', ') || 'none'}. Rule version:{' '}
            {detail.display.identity.rule_version}.
          </p>
          {detail.display.diagnostic && (
            <p>
              Geometry diagnostic: {detail.display.diagnostic}. Drawable:{' '}
              {String(detail.display.drawable)}.
            </p>
          )}
          {detail.display.geometry_omitted && (
            <p>
              Geometry omitted: {detail.display.geometry_omitted}. Tags and classification are
              available below.
            </p>
          )}
          <details open>
            <summary>Original tags</summary>
            <dl>
              {Object.entries(detail.properties).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{showValue(value)}</dd>
                </div>
              ))}
            </dl>
          </details>
          {layers.map(
            ({ key }) =>
              detail.layer_analyses?.[key] && (
                <CostDetails key={key} layer={key} analysis={detail.layer_analyses[key]!} />
              ),
          )}
        </>
      )}
    </section>
  )
}
