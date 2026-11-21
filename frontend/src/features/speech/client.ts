import { ApiRequestError } from '../../api'
import { request } from '../../api'
import type { Language } from '../document-upload/validation'

export const TTS_MAX_CHARS = 1000

/** API-09: 텍스트를 CLOVA Voice mp3 로 받는다. 성공 응답은 JSON 봉투가 아닌 audio/mpeg 이다. */
export async function synthesizeSpeech(text: string, lang: Language, signal?: AbortSignal): Promise<Blob> {
  const res = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text.trim().slice(0, TTS_MAX_CHARS), lang }), signal })
  if (res.ok && (res.headers.get('content-type') ?? '').startsWith('audio/')) return res.blob()
  const body = await res.json().catch(() => null) as { error?: { code: string; message: string } } | null
  throw new ApiRequestError(body?.error ?? { code: 'INTERNAL_ERROR', message: `음성을 만들지 못했어요. (HTTP ${res.status})` })
}

/** API-10: 답변 문장 번역 (Papago). 한국어면 그대로 돌려준다. */
export async function translateText(text: string, target: Language, signal?: AbortSignal): Promise<string> {
  if (target === 'ko') return text
  const res = await request<{ texts: string[]; target: Language }>('/translate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texts: [text], target }), signal })
  if (!res.texts?.[0]?.trim()) throw new Error('번역 응답을 확인하지 못했어요.')
  return res.texts[0]
}
