import type { ReactNode } from 'react'
import { fieldLabel } from './sourcePresentation'

export function SourceFacts({ title, children }: { title: string; children: ReactNode }) {
  return <section className="source-card" aria-label={title}><h4>{title}</h4>{children}</section>
}

export function Fact({ label, children }: { label: string; children: ReactNode }) {
  return <div className="source-fact"><dt>{label}</dt><dd>{children}</dd></div>
}

export function AttributeValue({ value }: { value: unknown }) {
  if (value == null) return <span className="source-missing">Not supplied</span>
  if (Array.isArray(value)) return value.length ? <ol className="source-attribute-list">{value.map((item, index) => <li key={index}><AttributeValue value={item} /></li>)}</ol> : <span>No entries</span>
  if (typeof value === 'object') return <AttributeList values={value as Record<string, unknown>} />
  if (typeof value === 'boolean') return <span>{value ? 'Yes' : 'No'}</span>
  return <span>{String(value)}</span>
}

export function AttributeList({ values }: { values: Record<string, unknown> }) {
  const entries = Object.entries(values)
  return entries.length ? <dl className="source-attributes">{entries.map(([key, value]) => <Fact key={key} label={fieldLabel(key)}><AttributeValue value={value} /></Fact>)}</dl> : <p>No attributes supplied.</p>
}

export function OriginalAttributes({ values, title = 'Original attributes' }: { values: Record<string, unknown>; title?: string }) {
  return <>
    <details className="source-disclosure"><summary>{title}</summary><AttributeList values={values} /></details>
    <details className="source-disclosure source-raw"><summary>Advanced: raw JSON</summary><pre>{JSON.stringify(values, null, 2)}</pre></details>
  </>
}
