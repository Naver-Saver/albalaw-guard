import type { ReactNode } from 'react'
import { Icon } from './Icon'

export function Badge({ tone = 'neutral', children }: { tone?: 'neutral' | 'success' | 'warning'; children: ReactNode }) {
  return <span className={`badge badge--${tone}`}>{tone !== 'neutral' && <Icon name={tone === 'success' ? 'check' : 'info'} width="14" height="14" />}{children}</span>
}

export function StatePanel({ status, title, description, action }: { status: 'loading' | 'error' | 'empty'; title: string; description?: string; action?: ReactNode }) {
  return <div className={`state-panel state-panel--${status}`} role={status === 'error' ? 'alert' : 'status'} aria-live="polite" aria-atomic="true">
    <div className="state-panel__icon">{status === 'loading' ? <span className="spinner" aria-hidden="true" /> : <Icon name={status === 'error' ? 'warning' : 'file'} width="24" height="24" />}</div>
    <h3>{title}</h3>{description && <p>{description}</p>}{action}
  </div>
}
