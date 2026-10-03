import { useId, useState, type ReactNode } from 'react'

export default function CollapsiblePanel({
  title,
  className = '',
  defaultExpanded = true,
  ariaLabel,
  badge,
  children,
}: {
  title: string
  className?: string
  defaultExpanded?: boolean
  ariaLabel?: string
  badge?: ReactNode
  children: ReactNode
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const id = useId()
  return (
    <section className={className} aria-label={ariaLabel ?? title}>
      <div className="panel-heading">
        <h3>
          {title} {badge}
        </h3>
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={id}
          aria-label={`${expanded ? 'Collapse' : 'Expand'} ${title}`}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      <div id={id} hidden={!expanded}>
        {children}
      </div>
    </section>
  )
}
