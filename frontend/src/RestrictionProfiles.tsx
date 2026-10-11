import { useEffect, useState } from 'react'
import { getJson, postJson } from './api'
import { scenarioInterval } from './scenarioTime'
import './restrictionProfiles.css'

export interface RestrictionReport {
  counts: Record<string, number>
  decisions: { source: string; source_signature: string; state: string; reason: string }[]
  coverage: { status: string; reason: string; temporary_features?: number; reviewed_notices?: number }
  policy_exclusions?: number
  building_counts?: Record<string, number>
}
interface Profile {
  schema_version: number; name: string; id?: string
  zone_assessments: Record<string, unknown>; notices: unknown[]
}
const empty: Profile = { schema_version: 1, name: '', zone_assessments: {}, notices: [] }

export default function RestrictionProfiles({ datasetId, report, start, end, onSelect }: {
  datasetId: string; report?: RestrictionReport; start: string; end: string
  onSelect: (id: string) => void
}) {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [draft, setDraft] = useState<Profile>(empty)
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [entry, setEntry] = useState({ source: '', state: 'prohibited', evidence: '', conditions: '', phase: 'transit', lower: 100, upper: 120, start: '', end: '' })
  useEffect(() => {
    const active = new AbortController()
    getJson<{ profiles: Profile[]; errors: unknown[] }>(`/api/datasets/${encodeURIComponent(datasetId)}/study/restriction-profiles`, active.signal)
      .then(value => { if (!active.signal.aborted) { setProfiles(value.profiles ?? []); if (value.errors?.length) setError('Some saved profiles failed integrity checks.') } })
      .catch(err => { if (!active.signal.aborted) setError(err.message) })
    return () => active.abort()
  }, [datasetId])
  function select(id: string) {
    setSelected(id); setDraft(profiles.find(p => p.id === id) ?? empty); setError(''); onSelect(id)
  }
  function changed(next: Profile) {
    setDraft(next); setSelected(''); if (selected) onSelect('')
  }
  function add() {
    try {
      const zone = report?.decisions.find(item => item.source === entry.source)
      if (!zone) throw new Error('Load scenario layers, then select a zone.')
      if (!entry.evidence.trim()) throw new Error('Enter evidence for this assessment.')
      const dates = scenarioInterval(entry.start || start, entry.end || end)
      const conditions = entry.conditions.split('\n').map(c => c.trim()).filter(Boolean)
      if (entry.state === 'conditional_allowed' && !conditions.length) throw new Error('List the conditions satisfied by the evidence.')
      changed({ ...draft, zone_assessments: { ...draft.zone_assessments, [zone.source]: {
        source_signature: zone.source_signature, state: entry.state, evidence: entry.evidence,
        scenario: 'civil', phase: entry.phase, agl_interval_m: [entry.lower, entry.upper],
        valid_from: dates.mission_start, valid_until: dates.mission_end, conditions_satisfied: conditions,
      } } }); setError('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Cannot add assessment.') }
  }
  async function save() {
    setSaving(true); setError('')
    try {
      const saved = await postJson<Profile>(`/api/datasets/${encodeURIComponent(datasetId)}/study/restriction-profiles`, draft)
      setProfiles(current => [...current, saved]); setDraft(saved); setSelected(saved.id!); onSelect(saved.id!)
    } catch (err) { setError(err instanceof Error ? err.message : 'Cannot save profile.') }
    finally { setSaving(false) }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(draft, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = 'restriction-profile.json'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <details className="restriction-profile"><summary>Restriction assessments and reviewed notices</summary>
    <p>Save evidence for each zone. Launch or landing consent does not allow transit. Import reviewed official notices as a profile; every revision is saved separately.</p>
    <label>Restriction profile<select aria-label="Restriction profile" value={selected} onChange={event => select(event.target.value)}><option value="">No saved profile</option>{profiles.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id?.slice(0, 8)})</option>)}</select></label>
    <label>Profile name<input value={draft.name} onChange={event => changed({ ...draft, name: event.target.value })} /></label>
    <label>Import reviewed profile<input type="file" accept=".json,application/json" onChange={async event => {
      try { const file = event.target.files?.[0]; if (!file) return; if (file.size > 2_000_000) throw new Error('Profile exceeds 2 MB.'); const imported = JSON.parse(await file.text()) as Profile
        if (imported.schema_version !== 1 || !imported.name || !imported.zone_assessments || !Array.isArray(imported.notices)) throw new Error('Invalid profile format.'); changed(imported); setError('')
      } catch (err) { setError(err instanceof Error ? err.message : 'Cannot import profile.') }
    }} /></label>
    <fieldset><legend>Add a zone assessment</legend>
      <label>Assessed zone<select aria-label="Assessed zone" value={entry.source} onChange={event => setEntry({ ...entry, source: event.target.value })}><option value="">Load layers and select zone</option>{report?.decisions.map(z => <option key={z.source} value={z.source}>{z.source} — {z.state}</option>)}</select></label>
      <label>Assessment decision<select aria-label="Assessment decision" value={entry.state} onChange={event => setEntry({ ...entry, state: event.target.value })}><option value="prohibited">Prohibited with evidence</option><option value="conditional_allowed">Conditions satisfied with evidence</option></select></label>
      <label>Permission phase<select aria-label="Permission phase" value={entry.phase} onChange={event => setEntry({ ...entry, phase: event.target.value })}>{['transit', 'launch', 'landing', 'all'].map(p => <option key={p}>{p}</option>)}</select></label>
      <label>Assessment valid from<input type="datetime-local" value={entry.start} onChange={event => setEntry({ ...entry, start: event.target.value })} /></label>
      <label>Assessment valid until<input type="datetime-local" value={entry.end} onChange={event => setEntry({ ...entry, end: event.target.value })} /></label>
      <p>Blank validity fields use the scenario interval. Enter Europe/Berlin local times.</p>
      <label>Assessment minimum AGL (m)<input type="number" min="0" max="10000" value={entry.lower} onChange={event => setEntry({ ...entry, lower: Number(event.target.value) })} /></label>
      <label>Assessment maximum AGL (m)<input type="number" min="0" max="10000" value={entry.upper} onChange={event => setEntry({ ...entry, upper: Number(event.target.value) })} /></label>
      <label>Assessment evidence<textarea value={entry.evidence} onChange={event => setEntry({ ...entry, evidence: event.target.value })} /></label>
      <label>Satisfied conditions (one per line)<textarea value={entry.conditions} onChange={event => setEntry({ ...entry, conditions: event.target.value })} /></label>
      <button type="button" onClick={add}>Add assessment to draft</button>
    </fieldset>
    <p>{Object.keys(draft.zone_assessments).length} assessments · {draft.notices.length} reviewed notices. Unsaved changes are not used for planning.</p>
    <button type="button" disabled={saving || !draft.name.trim()} onClick={() => void save()}>{saving ? 'Saving profile…' : 'Save and use profile revision'}</button>
    <button type="button" onClick={download}>Export assessment profile</button>
    <details><summary>Review profile evidence</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: '20rem', overflow: 'auto' }}>{JSON.stringify(draft, null, 2)}</pre></details>
    {error && <p role="alert">{error}</p>}
  </details>
}
