import { request } from '../../api'
import type { OcrResult, PreparedDocument, ReviewRequest } from './model'
import type { ReviewResult } from '../check-results/types'

export function extractDocument(document: PreparedDocument, signal: AbortSignal) {
  const body = new FormData()
  body.append('file', document.file)
  body.append('doc_type', document.docType)
  return request<OcrResult>('/contracts/ocr', { method: 'POST', body, signal })
}
export function reviewContract(payload: ReviewRequest, signal: AbortSignal) {
  return request<ReviewResult>('/contracts/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal })
}
