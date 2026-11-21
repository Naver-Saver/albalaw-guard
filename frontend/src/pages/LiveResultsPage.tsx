import { ResultTranslation } from '../components/ResultTranslation'
import { useEffect, useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { StatePanel, Badge } from '../components/common/Status'
import type { ReviewRequest } from '../features/document-review/model'
import type { ReviewResult } from '../features/check-results/types'
import { reviewContract } from '../features/document-review/client'
import { safeOfficialUrl } from '../features/check-results/sourceUrl'
import './results.css'

export function LiveResultsPage({ payload, onEdit, cachedResult, onResult }: { payload: ReviewRequest; onEdit: () => void; cachedResult: ReviewResult | null; onResult: (result: ReviewResult) => void }) {
  const [result, setResult] = useState<ReviewResult | null>(cachedResult)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (cachedResult) return
    const controller = new AbortController()
    reviewContract(payload, controller.signal).then(value => { if (!controller.signal.aborted) { setResult(value); onResult(value) } }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '서버에 연결하지 못했어요.') })
    return () => controller.abort()
  }, [payload, attempt, cachedResult, onResult])
  if (error) return <StatePanel status="error" title="점검 결과를 가져오지 못했어요" description={error} action={<><Button onClick={() => { setError(''); setResult(null); setAttempt(value => value + 1) }}>다시 시도</Button><Button variant="secondary" onClick={onEdit}>입력 수정</Button></>} />
  if (!result) return <StatePanel status="loading" title="입력한 내용으로 점검하고 있어요" description="서버에서 계산 결과와 공식 근거를 확인하고 있어요." action={<Button variant="secondary" onClick={onEdit}>입력으로 돌아가기</Button>} />
  const calc = result.calculation
  return <ResultTranslation key={payload.lang} result={result} target={payload.lang}>{display => <><div className="results-heading"><div><p className="eyebrow">YOUR REVIEW</p><h1>입력한 내용의 점검 결과예요</h1><p>확인한 입력값을 바탕으로 서버에서 계산했어요.</p></div><Badge>서버 응답</Badge></div>
    <p>설명과 확인 항목은 선택한 언어로 안내해요. 번역문은 한국어 원문과 함께 확인해 주세요.</p>
    <div className="calculation-grid">{[['적용 연도', `${calc.year}년`], ['최저시급', `${calc.minimum_hourly.toLocaleString('ko-KR')}원`], ['시간당 차이', `${calc.shortfall_per_hour.toLocaleString('ko-KR')}원`], ['주휴수당 계산값', `${calc.weekly_holiday_pay.toLocaleString('ko-KR')}원`]].map(([label, value]) => <div className="calculation-card" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><p className="calculation-caption">{calc.notice} · 입력 시급 {payload.hourly_wage.toLocaleString('ko-KR')}원 · 주 {payload.weekly_hours}시간</p>
    <div className="results-grid"><div className="results-primary"><Card title="확인할 항목">{display.items.map(item => <details className="check-item" key={item.title} open><summary><Badge tone={item.level === 'check' ? 'warning' : 'success'}>{item.level === 'check' ? '확인 필요' : '확인 항목'}</Badge><strong>{item.title}</strong></summary><p>{item.description}</p></details>)}</Card><Card title="쉬운 설명"><p className="result-explanation">{display.sources.length && display.explanation ? display.explanation : '설명 또는 근거를 가져오지 못했어요. 계산값과 원문을 확인하거나 상담을 이용해 주세요.'}</p></Card></div><Card title="공식 근거">{display.sources.length ? display.sources.map(source => { const url = safeOfficialUrl(source.url); return <article className="source-card" key={source.id}><h3>{source.title}</h3><p>{source.snippet}</p>{url ? <a className="source-link" href={url} target="_blank" rel="noreferrer">원문 열기 (새 탭)</a> : <p>원문 링크를 확인할 수 없어요.</p>}</article> }) : <p>연결된 근거가 없어요.</p>}</Card></div>
    <div className="results-actions"><Button variant="secondary" onClick={onEdit}>입력 내용 수정</Button></div><aside className="consultation"><p>{display.disclaimer}</p></aside>
  </>}</ResultTranslation>
}
