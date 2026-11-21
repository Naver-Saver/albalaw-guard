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
export function askVoice(file: File, signal: AbortSignal) {
  if (!file.size || file.size > 10 * 1024 * 1024 || !/\.wav$/i.test(file.name)) return Promise.reject(new Error('60초 이하 WAV 음성을 준비해 주세요.'))
  const body = new FormData(); body.append('file', file)
  return request<AskResult>('/ask/voice', { method: 'POST', body, signal })
}
