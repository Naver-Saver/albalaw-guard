import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost'; loading?: boolean }

export function Button({ variant = 'primary', loading = false, disabled, children, className = '', type = 'button', ...props }: ButtonProps) {
  return <button {...props} type={type} className={`button button--${variant} ${className}`} disabled={disabled || loading} aria-busy={loading || undefined}>
    {loading && <span className="spinner" aria-hidden="true" />}{children}
  </button>
}
