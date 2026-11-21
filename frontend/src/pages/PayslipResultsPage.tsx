import { useEffect, useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Badge, StatePanel } from '../components/common/Status'
import { SourceDetail } from '../components/SourceDetail'
import { reviewPayslip } from '../features/payslip/client'
import type { PayslipRequest, PayslipResult } from '../features/payslip/model'
import { safeOfficialUrl } from '../features/check-results/sourceUrl'
import './results.css'

const won = (value: number | null | undefined) => (value === null || value === undefined ? '미기재' : `${value.toLocaleString('ko-KR')}원`)

export function PayslipResultsPage({ payload, onEdit, cachedResult, onResult }: { payload: PayslipRequest; onEdit: () => void; cachedResult: PayslipResult | null; onResult: (result: PayslipResult) => void }) {
  const [result, setResult] = useState<PayslipResult | null>(cachedResult)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (cachedResult) return
    const controller = new AbortController()
    reviewPayslip(payload, controller.signal).then(value => { if (!controller.signal.aborted) { setResult(value); onResult(value) } }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '서버에 연결하지 못했어요.') })
    return () => controller.abort()
  }, [payload, attempt, cachedResult, onResult])
  if (error) return <StatePanel status="error" title="급여명세서 점검 결과를 가져오지 못했어요" description={error} action={<><Button onClick={() => { setError(''); setResult(null); setAttempt(value => value + 1) }}>다시 시도</Button><Button variant="secondary" onClick={onEdit}>입력 수정</Button></>} />
  if (!result) return <StatePanel status="loading" title="급여명세서를 점검하고 있어요" description="합계 검산, 필수 기재 항목, 최저임금과 근거를 확인하고 있어요." />
  const t = result.totals
  const checkCount = result.items.filter(item => item.level === 'check').length
  return <>
    <div className="results-heading"><div><p className="eyebrow">YOUR PAYSLIP</p><h1>급여명세서 점검 결과예요</h1><p>확인한 입력값으로 서버에서 검산했어요.</p></div><Badge>서버 응답</Badge></div>
    <section className="results-summary"><div><Badge tone={checkCount ? 'warning' : 'success'}>{checkCount ? '확인 필요' : '특이사항 없음'}</Badge><h2>확인할 항목이 {checkCount}개 있어요</h2><p>아래 항목과 근거를 하나씩 확인해 보세요.</p></div><Button variant="secondary" onClick={onEdit}>입력 내용 수정</Button></section>
    <div className="calculation-grid">{[['지급 항목 합계', won(t.items_sum)], ['공제 항목 합계', won(t.deductions_sum)], ['명세서 지급총액', won(t.total_pay)], ['계산상 실지급액', won(t.expected_net_pay)]].map(([label, value]) => <div className="calculation-card" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
    {t.mismatches.length > 0 && <p className="calculation-caption" role="status">{t.mismatches.map(m => `${m.field === 'totalPay' ? '지급총액' : '실지급액'}: 명세서 ${won(m.actual)} / 계산 ${won(m.expected)} (차이 ${won(Math.abs(m.difference))})`).join(' · ')}</p>}
    {result.wage && <p className="calculation-caption">{result.wage.year}년 최저시급 {won(result.wage.minimum_wage)} · 입력 시급 {won(result.wage.hourly_wage)}{result.wage.weekly_holiday_eligible ? ` · 주휴수당 계산값 주 ${won(result.wage.weekly_holiday_pay)}` : ''}</p>}
    <div className="results-grid"><div className="results-primary">
      <Card title="확인할 항목">{result.items.length ? result.items.map(item => <details className="check-item" key={item.title} open><summary><Badge tone={item.level === 'check' ? 'warning' : 'success'}>{item.level === 'check' ? '확인 필요' : '확인 항목'}</Badge><strong>{item.title}</strong></summary><p>{item.description}</p></details>) : <p className="results-muted">표시할 항목이 없어요.</p>}</Card>
      {result.missing.length > 0 && <Card title="명세서에 없는 항목">{<ul>{result.missing.map(m => <li key={m.field_key}>{m.item}{m.conditional ? ' (상황에 따라 없어도 될 수 있어요)' : ''}</li>)}</ul>}</Card>}
    </div><Card title="공식 근거">{result.sources.length ? result.sources.map(source => { const href = safeOfficialUrl(source.url); return <article className="source-card" key={source.id}><h3>{source.title}</h3>{source.snippet && <p>{source.snippet}</p>}<SourceDetail id={source.id} />{href && <a className="source-link" href={href} target="_blank" rel="noreferrer">국가법령정보센터에서 열기 (새 탭)</a>}</article> }) : <p>연결된 근거가 없어요.</p>}</Card></div>
    <aside className="consultation"><p>{result.disclaimer}</p></aside>
  </>
}
