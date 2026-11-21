import { useId } from 'react'
import type { ReactNode } from 'react'

export function Card({ title, description, action, children, className = '' }: { title: string; description?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  const titleId = useId()
  return <section className={`card ${className}`} aria-labelledby={titleId}>
    <div className="card__header"><div><h2 id={titleId}>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>{children}
  </section>
}
