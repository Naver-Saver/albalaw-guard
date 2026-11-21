import type { Language } from '../document-upload/validation'
import type { ExtractedField, PreparedDocument } from '../document-review/model'
import type { CheckItem, Source } from '../check-results/types'

// API-03 (doc_type=payslip) 응답의 payslip 부분
export type PayslipOcrLine = { name: string; amount: number; source_text: string }
export type PayslipOcr = {
  employee_name: string | null; pay_date: string | null; items: PayslipOcrLine[]; deductions: PayslipOcrLine[]
  total_pay: ExtractedField<number>; net_pay: ExtractedField<number>; calculation_method: string | null
}

export type PayslipLineDraft = { name: string; amount: string; source?: string }
export type PayslipDraft = {
  employee_name: string; pay_date: string; items: PayslipLineDraft[]; deductions: PayslipLineDraft[]
  total_pay: string; net_pay: string; calculation_method: string; hourly_wage: string; weekly_hours: string; year: string
}
export type PayslipSession = { document: PreparedDocument; rawText: string; draft: PayslipDraft; initialDraft: PayslipDraft; confirmed: boolean; language: Language }
export type PayslipErrors = Partial<Record<'items' | 'deductions' | 'total_pay' | 'net_pay' | 'hourly_wage' | 'weekly_hours' | 'year', string>>

// API-14 요청
export type PayslipLine = { name: string; amount: number }
export type PayslipRequest = {
  employee_name?: string; pay_date?: string; items: PayslipLine[]; deductions: PayslipLine[]
  total_pay?: number; net_pay?: number; calculation_method?: string; hourly_wage?: number; weekly_hours?: number; year: number; lang: Language
}
// API-14 응답
export type PayslipResult = {
  totals: { items_sum: number; deductions_sum: number; total_pay: number | null; net_pay: number | null; expected_net_pay: number; total_matches: boolean | null; net_matches: boolean | null; mismatches: { field: 'totalPay' | 'netPay'; expected: number; actual: number; difference: number }[] }
  wage: { year: number; minimum_wage: number; hourly_wage: number; is_below_minimum: boolean; shortfall_per_hour: number; weekly_holiday_eligible: boolean; weekly_holiday_hours: number; weekly_holiday_pay: number } | null
  missing: { item: string; field_key: string; source_ids: string[]; conditional: boolean }[]
  items: CheckItem[]; sources: Source[]; disclaimer: string
}

const toLines = (lines: PayslipOcrLine[] = []): PayslipLineDraft[] => lines.map(line => ({ name: line.name, amount: String(line.amount), source: line.source_text }))
const num = (value: number | null | undefined) => (value === null || value === undefined ? '' : String(value))

/** OCR로 읽은 급여명세서 값을 확인 화면의 입력란에 그대로 채운다. */
export function createPayslipSession(document: PreparedDocument, rawText: string, ocr: PayslipOcr | null | undefined, year = new Date().getFullYear(), hourlyWage?: number | null): PayslipSession {
  const yearFromDate = ocr?.pay_date?.match(/20\d{2}/)?.[0]
  const draft: PayslipDraft = {
    employee_name: ocr?.employee_name ?? '', pay_date: ocr?.pay_date ?? '',
    items: toLines(ocr?.items), deductions: toLines(ocr?.deductions),
    total_pay: num(ocr?.total_pay?.value), net_pay: num(ocr?.net_pay?.value),
    calculation_method: ocr?.calculation_method ?? '', hourly_wage: num(hourlyWage), weekly_hours: '', year: yearFromDate ?? String(year),
  }
  if (!draft.items.length) draft.items.push({ name: '', amount: '' })
  return { document, rawText, draft, initialDraft: structuredClone(draft), confirmed: false, language: document.language }
}

const isAmount = (value: string) => /^(?:\d+|\d{1,3}(?:,\d{3})+)$/.test(value.trim())
const toAmount = (value: string) => Number(value.trim().replaceAll(',', ''))
const filled = (lines: PayslipLineDraft[]) => lines.filter(line => line.name.trim() || line.amount.trim())

export function validatePayslipDraft(draft: PayslipDraft): PayslipErrors {
  const errors: PayslipErrors = {}
  const badLine = (lines: PayslipLineDraft[]) => filled(lines).some(line => !line.name.trim() || !isAmount(line.amount))
  if (!filled(draft.items).length) errors.items = '지급 항목을 1개 이상 입력해 주세요.'
  else if (badLine(draft.items)) errors.items = '항목 이름과 금액(0 이상의 정수)을 모두 입력해 주세요.'
  if (badLine(draft.deductions)) errors.deductions = '공제 항목 이름과 금액을 모두 입력해 주세요.'
  if (draft.total_pay.trim() && !isAmount(draft.total_pay)) errors.total_pay = '지급총액을 숫자로 입력해 주세요.'
  if (draft.net_pay.trim() && !isAmount(draft.net_pay)) errors.net_pay = '실지급액을 숫자로 입력해 주세요.'
  if (draft.hourly_wage.trim() && (!isAmount(draft.hourly_wage) || toAmount(draft.hourly_wage) <= 0)) errors.hourly_wage = '시급을 1원 이상의 정수로 입력해 주세요.'
  if (draft.weekly_hours.trim() && (!/^\d+(?:\.\d+)?$/.test(draft.weekly_hours.trim()) || Number(draft.weekly_hours) <= 0 || Number(draft.weekly_hours) > 168)) errors.weekly_hours = '주 근무시간을 0~168시간 사이로 입력해 주세요.'
  if (!/^\d{4}$/.test(draft.year.trim()) || Number(draft.year) < 1900) errors.year = '적용 연도를 네 자리 숫자로 입력해 주세요.'
  return errors
}

export function toPayslipRequest(session: PayslipSession): PayslipRequest {
  const d = session.draft
  if (!session.confirmed || Object.keys(validatePayslipDraft(d)).length) throw new Error('입력값과 원본 확인 동의를 확인해 주세요.')
  const lines = (list: PayslipLineDraft[]) => filled(list).map(line => ({ name: line.name.trim(), amount: toAmount(line.amount) }))
  const optional = <T,>(cond: boolean, value: T) => (cond ? value : undefined)
  const body: PayslipRequest = {
    items: lines(d.items), deductions: lines(d.deductions), year: Number(d.year.trim()), lang: session.language,
    employee_name: optional(Boolean(d.employee_name.trim()), d.employee_name.trim()),
    pay_date: optional(Boolean(d.pay_date.trim()), d.pay_date.trim()),
    total_pay: optional(Boolean(d.total_pay.trim()), toAmount(d.total_pay)),
    net_pay: optional(Boolean(d.net_pay.trim()), toAmount(d.net_pay)),
    calculation_method: optional(Boolean(d.calculation_method.trim()), d.calculation_method.trim()),
    hourly_wage: optional(Boolean(d.hourly_wage.trim()), toAmount(d.hourly_wage)),
    weekly_hours: optional(Boolean(d.weekly_hours.trim()), Number(d.weekly_hours.trim())),
  }
  return JSON.parse(JSON.stringify(body)) as PayslipRequest // undefined 키 제거
}
