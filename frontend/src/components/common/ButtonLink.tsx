import type { AnchorHTMLAttributes } from 'react'

export function ButtonLink({ variant = 'primary', className = '', ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { variant?: 'primary' | 'secondary' | 'ghost' }) {
  return <a {...props} className={`button button--${variant} ${className}`} />
}
