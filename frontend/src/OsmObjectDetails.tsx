import { useEffect, useState } from 'react'
import { getJson } from './api'
import { layers, type OsmObjectDetail } from './types'
import { snapshotKey, useMapSelection } from './mapSelection'
import { AttributeList, Fact, OriginalAttributes, SourceFacts } from './SourceFacts'
import { categoryNames, objectTitle, sourceText } from './sourcePresentation'
import RegionalOsmCosts from './RegionalOsmCosts'

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
      <h3>{detail ? objectTitle(detail.properties) : 'OSM object'}</h3>
      <p className="source-identity">OSM {selection.key}</p>
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
          <SourceFacts title="Original source facts"><dl>
            <Fact label="Category membership">{categoryNames(detail.display.categories) || 'None supplied'}</Fact>
            {['height', 'min_height', 'building:levels', 'building:min_level'].filter(key => sourceText(detail.properties[key]) != null).map(key => {
              const raw = sourceText(detail.properties[key])!
              const isHeight = key === 'height' || key === 'min_height'
              const value = isHeight && /^\d+(\.\d+)?$/.test(raw) ? `${raw} m` : raw
              return <Fact key={key} label={{ height: 'Height (source tag)', min_height: 'Minimum height (source tag)', 'building:levels': 'Building levels', 'building:min_level': 'Minimum building level' }[key]!}>{value}{!isHeight && ' · levels, not a measured height'}</Fact>
            })}
            {['addr:street', 'addr:housenumber', 'addr:postcode', 'addr:city', 'addr:country'].some(key => sourceText(detail.properties[key])) && <Fact label="Address">{['addr:street', 'addr:housenumber', 'addr:postcode', 'addr:city', 'addr:country'].map(key => sourceText(detail.properties[key])).filter(Boolean).join(' ')}</Fact>}
          </dl>{sourceText(detail.properties.height) == null && <p>Height not supplied by original tags.</p>}
          <p>Original map tags describe the source object; they do not establish current flight permission.</p></SourceFacts>
          {detail.display.tags_complete === false && <p className="source-interpretation">Original tags are incomplete; absent fields may be unavailable in this response.</p>}
          {detail.display.classification_complete === false && <p className="source-interpretation">Category classification is incomplete; the displayed costs do not cover every source tag.</p>}
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
          {layers.map(
            ({ key }) =>
              detail.layer_analyses?.[key] && (
                <RegionalOsmCosts key={key} layer={key} analysis={detail.layer_analyses[key]!} />
              ),
          )}
          {!Object.values(detail.layer_analyses ?? {}).some(Boolean) && <p>No category cost analysis supplied for this object.</p>}
          <OriginalAttributes values={detail.properties} title="Original tags" />
          <details className="source-disclosure"><summary>OSM provenance and completeness</summary><AttributeList values={{ source_identity: detail.display.identity, tags_complete: detail.display.tags_complete, classification_complete: detail.display.classification_complete, geometry_complete: detail.display.geometry_complete }} /></details>
        </>
      )}
    </section>
  )
}
