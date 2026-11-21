import { request } from '../../api'
import type { PayslipRequest, PayslipResult } from './model'

export function reviewPayslip(payload: PayslipRequest, signal: AbortSignal) {
  return request<PayslipResult>('/payslips/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal })
}
