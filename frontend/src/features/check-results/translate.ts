import { request } from '../../api'
import type { ReviewResult } from './types'
import type { Language } from '../document-upload/validation'

export async function translateReview(result: ReviewResult, target: Language, signal: AbortSignal): Promise<ReviewResult> {
  const copy = structuredClone(result)
  if (target === 'ko') return copy
  // Only explanatory prose is translated. Calculation, original sources and titles stay intact.
  const texts = result.items.flatMap(item => [item.title, item.description])
  const hasExplanation = Boolean(result.explanation && result.sources.length)
  if (hasExplanation) texts.push(result.explanation!)
  texts.push(result.disclaimer)
  const translated: string[] = []
  for (let i = 0; i < texts.length; i += 30) {
    const batch = texts.slice(i, i + 30)
    const response: { texts: string[]; target: Language } = await request('/translate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texts: batch, target }), signal })
    if (response.target !== target || response.texts.length !== batch.length || response.texts.some(text => typeof text !== 'string' || !text.trim())) throw new Error('번역 응답을 확인하지 못했어요.')
    translated.push(...response.texts)
  }
  let i = 0
  copy.items = copy.items.map(item => ({ ...item, title: translated[i++], description: translated[i++] }))
  copy.explanation = hasExplanation ? translated[i++] : null
  copy.disclaimer = translated[i]
  return copy
}
