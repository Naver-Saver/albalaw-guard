import { useId } from 'react'
import type { ComponentPropsWithRef, InputHTMLAttributes, SelectHTMLAttributes, ReactNode } from 'react'
import { Icon } from './Icon'

type FieldContent = { label: string; hint?: string; error?: string }

export function InputField({ label, hint, error, id, ...props }: ComponentPropsWithRef<'input'> & FieldContent) {
  const generatedId = useId()
  const fieldId = id ?? generatedId
  const descriptionId = hint || error ? `${fieldId}-description` : undefined
  const descriptions = [props['aria-describedby'], descriptionId].filter(Boolean).join(' ') || undefined
  return <div className="field">
    <label htmlFor={fieldId}>{label}{props.required && <span className="field__required"> (필수)</span>}</label>
    <input {...props} id={fieldId} className={`control ${props.className ?? ''}`} aria-invalid={error ? true : props['aria-invalid']} aria-describedby={descriptions} />
    {(error || hint) && <p id={descriptionId} className={`field__hint ${error ? 'field__hint--error' : ''}`}>{error || hint}</p>}
  </div>
}

export function SelectField({ label, hint, error, id, children, ...props }: SelectHTMLAttributes<HTMLSelectElement> & FieldContent) {
  const generatedId = useId()
  const fieldId = id ?? generatedId
  const descriptionId = hint || error ? `${fieldId}-description` : undefined
  const descriptions = [props['aria-describedby'], descriptionId].filter(Boolean).join(' ') || undefined
  return <div className="field">
    <label htmlFor={fieldId}>{label}{props.required && <span className="field__required"> (필수)</span>}</label>
    <div className="select-wrap"><select {...props} id={fieldId} className={`control ${props.className ?? ''}`} aria-invalid={error ? true : props['aria-invalid']} aria-describedby={descriptions}>{children}</select><Icon name="chevron" /></div>
    {(error || hint) && <p id={descriptionId} className={`field__hint ${error ? 'field__hint--error' : ''}`}>{error || hint}</p>}
  </div>
}

export function Checkbox({ label, id, className = '', ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: ReactNode }) {
  const generatedId = useId()
  const fieldId = id ?? generatedId
  return <label className={`checkbox ${className}`} htmlFor={fieldId}><input {...props} type="checkbox" id={fieldId} /><span>{label}</span></label>
}
