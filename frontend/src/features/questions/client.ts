import { request } from '../../api'
import type { Source } from '../check-results/types'

export type AskResult = { question: string; route: 'faq' | 'studio' | 'none'; answer: string; sources: Source[] }
export function validateQuestion(value: string): string | null {
  const length = Array.from(value.trim()).length
  return length < 2 || length > 300 ? '질문을 2~300자로 입력해 주세요.' : null
}
export function askText(question: string, signal: AbortSignal) {
  const error = validateQuestion(question)
  if (error) return Promise.reject(new Error(error))
  return request<AskResult>('/ask/text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: question.trim() }), signal })
}
