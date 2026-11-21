import { useEffect, useState } from 'react'
import { fetchLawSource } from '../features/law/client'
import type { LawSource } from '../features/law/client'

/** 근거 카드 안에서 원문 전체를 펼쳐 보는 영역. 처음 펼칠 때만 서버에서 가져온다 (API-12). */
export function SourceDetail({ id }: { id: string }) {
  const [open, setOpen] = useState(false)
  const [source, setSource] = useState<LawSource | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!open || source) return
    const controller = new AbortController()
    fetchLawSource(id, controller.signal).then(setSource).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '원문을 불러오지 못했어요.') })
    return () => controller.abort()
  }, [open, id, source])
  return <details className="source-detail" onToggle={event => setOpen((event.currentTarget as HTMLDetailsElement).open)}>
    <summary>근거 원문 보기</summary>
    {error ? <p role="alert">{error}</p> : source ? <div><strong>{source.title}</strong><pre>{source.text}</pre></div> : <p role="status">원문을 불러오고 있어요.</p>}
  </details>
}
