import type { DocumentKind, DocumentType, Language } from '../document-upload/validation'
import { SAMPLE_OCR } from './sampleOcr'

export const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일'] as const
export type Weekday = typeof WEEKDAYS[number]
export type PreparedDocument = { file: File; kind: DocumentKind; docType: DocumentType; language: Language }
type ExtractedField<T> = { value: T | null; confidence: 'high' | 'low'; source_text?: string }
export type OcrResult = {
  doc_type: DocumentType
  raw_text: string
  extracted: { hourly_wage: ExtractedField<number>; weekly_hours: ExtractedField<number>; work_days: ExtractedField<Weekday[]>; break_minutes: ExtractedField<number> }
}
export type ReviewDraft = { hourly_wage: string; weekly_hours: string; work_days: Weekday[]; break_minutes: string; year: string }
export type ReviewErrors = Partial<Record<keyof ReviewDraft, string>>
export type ReviewSession = { mode: 'sample' | 'manual'; document: PreparedDocument | null; ocr: OcrResult | null; draft: ReviewDraft; initialDraft: ReviewDraft; confirmed: boolean; language: Language }
export type ReviewRequest = { hourly_wage: number; weekly_hours: number; work_days: Weekday[]; break_minutes?: number; year: number; lang: Language }

export function createReviewSession(mode: ReviewSession['mode'], document?: PreparedDocument, year = new Date().getFullYear()): ReviewSession {
  const ocr = mode === 'sample' ? structuredClone(SAMPLE_OCR) : null
  const draft: ReviewDraft = {
    hourly_wage: ocr?.extracted.hourly_wage.value?.toString() ?? '',
    weekly_hours: ocr?.extracted.weekly_hours.value?.toString() ?? '',
    work_days: [...(ocr?.extracted.work_days.value ?? [])],
    break_minutes: ocr?.extracted.break_minutes.value?.toString() ?? '',
    year: String(year),
  }
  return { mode, document: mode === 'manual' ? document ?? null : null, ocr, draft, initialDraft: structuredClone(draft), confirmed: false, language: document?.language ?? 'ko' }
}

export function validateReviewDraft(draft: ReviewDraft): ReviewErrors {
  const errors: ReviewErrors = {}
  const wage = draft.hourly_wage.trim()
  if (!/^(?:\d+|\d{1,3}(?:,\d{3})+)$/.test(wage) || !Number.isSafeInteger(Number(wage.replaceAll(',', '')))) errors.hourly_wage = '시급을 0 이상의 정수로 입력해 주세요.'
  const hours = draft.weekly_hours.trim()
  if (!/^\d+(?:\.\d+)?$/.test(hours) || !Number.isFinite(Number(hours)) || Number(hours) > 168) errors.weekly_hours = '주 근무시간을 0~168시간 사이로 입력해 주세요.'
  const minutes = draft.break_minutes.trim()
  if (minutes && (!/^\d+$/.test(minutes) || Number(minutes) > 1440)) errors.break_minutes = '휴게시간을 0~1,440분 사이의 정수로 입력해 주세요.'
  if (!/^\d{4}$/.test(draft.year.trim()) || Number(draft.year) < 1900) errors.year = '적용 연도를 네 자리 숫자로 입력해 주세요.'
  if (draft.work_days.some(day => !WEEKDAYS.includes(day)) || new Set(draft.work_days).size !== draft.work_days.length) errors.work_days = '근무요일을 중복 없이 선택해 주세요.'
  return errors
}

export function editReviewSession(session: ReviewSession, draft: ReviewDraft): ReviewSession {
  return { ...session, draft: { ...draft, work_days: [...draft.work_days] }, confirmed: false }
}

export function canConfirmReview(session: ReviewSession): boolean {
  return session.confirmed && Object.keys(validateReviewDraft(session.draft)).length === 0
}

export function toReviewRequest(session: ReviewSession): ReviewRequest {
  if (!canConfirmReview(session)) throw new Error('입력값과 원본 확인 동의를 확인해 주세요.')
  const draft = session.draft
  return {
    hourly_wage: Number(draft.hourly_wage.trim().replaceAll(',', '')),
    weekly_hours: Number(draft.weekly_hours.trim()),
    work_days: [...draft.work_days],
    ...(draft.break_minutes.trim() ? { break_minutes: Number(draft.break_minutes.trim()) } : {}),
    year: Number(draft.year.trim()),
    lang: session.language,
  }
}
