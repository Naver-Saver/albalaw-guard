import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Button } from './common/Button'
import type { Language } from '../features/document-upload/validation'
import type { ReviewResult } from '../features/check-results/types'
import { translateReview } from '../features/check-results/translate'

export function ResultTranslation({ result, target, children }: { result: ReviewResult; target: Language; children: (display: ReviewResult) => ReactNode }) {
  const [translated, setTranslated] = useState<ReviewResult | null>(null)
  const [error, setError] = useState('')
  const [original, setOriginal] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (target === 'ko') return
    const controller = new AbortController()
    translateReview(result, target, controller.signal).then(value => { if (!controller.signal.aborted) setTranslated(value) }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '번역하지 못했어요.') })
    return () => controller.abort()
  }, [result, target, attempt])
  const label = { ko: '한국어', en: 'English', vi: 'Tiếng Việt', 'zh-CN': '中文' }[target]
  return <>{target !== 'ko' && <div className="results-demo"><div><p role="status">{error ? `번역을 불러오지 못해 한국어 원문을 표시해요. ${error}` : translated ? `${label} 번역 · 계산값과 출처 제목·원문은 유지해요.` : '선택한 언어로 번역하고 있어요. 완료 전에는 한국어 원문을 표시해요.'}</p>{error && <Button variant="secondary" onClick={() => { setError(''); setAttempt(value => value + 1) }}>번역 다시 시도</Button>}{translated && <Button variant="secondary" onClick={() => setOriginal(value => !value)}>{original ? '번역 보기' : '한국어 원문 보기'}</Button>}</div></div>}{children(!original && translated ? translated : result)}</>
}
