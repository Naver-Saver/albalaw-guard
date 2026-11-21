import { useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Badge, StatePanel } from '../components/common/Status'
import { Icon } from '../components/common/Icon'
import type { ReviewRequest } from '../features/document-review/model'
import type { ResultScenario } from '../features/check-results/types'
import { getSampleResult } from '../features/check-results/sampleResult'
import { safeOfficialUrl } from '../features/check-results/sourceUrl'
import './results.css'

const scenarios: { value: ResultScenario; label: string }[] = [
  { value: 'ready', label: '기본 예시' }, { value: 'no-explanation', label: '설명 없음' },
  { value: 'no-sources', label: '근거 없음' }, { value: 'loading', label: '처리 중' }, { value: 'error', label: '오류' },
]
const won = (value: number) => `${value.toLocaleString('ko-KR')}원`

export function CheckResultsPage({ request, onEdit, onAsk, initialScenario = 'ready' }: { request: ReviewRequest; onEdit: () => void; onAsk: () => void; initialScenario?: ResultScenario }) {
  const [scenario, setScenario] = useState<ResultScenario>(initialScenario)
  const result = getSampleResult(scenario)
  const calculation = result.calculation
  const checkCount = result.items.filter(item => item.level === 'check').length
  const visibleExplanation = result.sources.length ? result.explanation : null
  const ready = scenario !== 'loading' && scenario !== 'error'

  return <>
    <div className="results-heading"><div><p className="eyebrow">UNDERSTAND YOUR WORK</p><h1>샘플 점검 결과를 살펴보세요</h1><p>확인할 항목과 공식 자료가 어떻게 표시되는지 알아보세요.</p></div><Badge>STEP 03 · 결과 예시</Badge></div>
    <div className="results-demo"><Icon name="info" /><p><strong>실제 요청은 보내지 않아요</strong>업로드 문서나 수정한 입력값으로 계산하지 않았어요. 아래 결과는 고정된 샘플 응답이며 실제 문서의 권리·의무를 판단하지 않아요.</p></div>
    <details className="results-input"><summary>내가 확인한 입력값 보기</summary><dl><div><dt>적용 연도</dt><dd>{request.year}년</dd></div><div><dt>입력 시급</dt><dd>{won(request.hourly_wage)}</dd></div><div><dt>주 근무시간</dt><dd>{request.weekly_hours}시간</dd></div><div><dt>근무요일</dt><dd>{request.work_days.join(' · ') || '미입력'}</dd></div><div><dt>하루 휴게시간</dt><dd>{request.break_minutes === undefined ? '미입력' : `${request.break_minutes}분`}</dd></div></dl><p>이 입력값과 아래 고정 샘플 계산값은 서로 연결되지 않아요.</p><Button variant="secondary" onClick={onEdit}>입력 내용 수정</Button></details>
    <details className="results-scenarios"><summary>다른 예시 상태 살펴보기</summary><fieldset><legend>결과 화면 예시 선택</legend>{scenarios.map(item => <label key={item.value}><input type="radio" name="result-scenario" value={item.value} checked={scenario === item.value} onChange={() => setScenario(item.value)} /><span>{item.label}</span></label>)}</fieldset><p>실제 오류나 처리 상황이 아니라 화면 상태를 바꾸는 체험이에요.</p></details>
    <div className="results-body" aria-live="polite" aria-atomic="false">
      {!ready ? <Card title={scenario === 'loading' ? '처리 중 화면 예시' : '오류 화면 예시'}>
        <StatePanel status={scenario === 'loading' ? 'loading' : 'error'} title={scenario === 'loading' ? '결과를 기다리는 화면이에요' : '결과를 불러오지 못한 상황이에요'} description="실제 요청은 보내지 않아요. 기본 예시로 돌아갈 수 있어요." action={<Button variant="secondary" onClick={() => setScenario('ready')}>{scenario === 'error' ? '다시 보기' : '기본 예시 보기'}</Button>} />
      </Card> : <>
        <section className="results-summary" aria-labelledby="results-summary-title"><span className="results-summary__icon"><Icon name="shield" width="26" height="26" /></span><div><Badge tone="warning">샘플 결과</Badge><h2 id="results-summary-title">확인할 항목이 {checkCount}개 있어요</h2><p>아래 샘플 항목과 안내를 하나씩 확인해 보세요.</p></div><Button variant="secondary" onClick={onEdit}>추출 내용 수정</Button></section>
        <section className="calculation-section" aria-labelledby="calculation-title"><div className="calculation-header"><h2 id="calculation-title">샘플 계산 응답</h2><Badge>고정 예시</Badge></div><p className="calculation-basis">예시 입력 · {calculation.year}년 · 시급 {won(calculation.hourly_wage)} · 주 {calculation.weekly_hours}시간</p><div className="calculation-grid">
          <div className="calculation-card"><span>적용 연도</span><strong>{calculation.year}<small>년</small></strong><p>입력한 연도와 별개인 샘플 기준</p></div>
          <div className="calculation-card"><span>기준 시급</span><strong>{calculation.minimum_hourly.toLocaleString('ko-KR')}<small>원</small></strong><p>{calculation.notice}</p></div>
          <div className="calculation-card calculation-card--check"><span>시간당 차이</span><strong>{calculation.shortfall_per_hour.toLocaleString('ko-KR')}<small>원</small></strong><p>고정 응답의 차액 표시 예시</p></div>
          <div className="calculation-card"><span>주휴수당 예시</span><strong>{calculation.weekly_holiday_pay.toLocaleString('ko-KR')}<small>원</small></strong><p>주휴시간 {calculation.weekly_holiday_hours}시간 · 대상 여부 별도 확인</p></div>
        </div><p className="calculation-caption">명세의 샘플 응답을 표시하며, 이 화면에서 금액을 계산하지 않아요.</p></section>
        <div className="results-grid"><div className="results-primary">
          <Card title="확인할 항목" description="항목을 펼쳐 예시 안내를 읽어보세요.">{result.items.length ? <div className="check-items">{result.items.map((item, index) => <details key={item.title} className="check-item" open={index === 0}><summary><Badge tone={item.level === 'check' ? 'warning' : 'success'}>{item.level === 'check' ? '확인 필요' : '확인 항목'}</Badge><strong>{item.title}</strong><Icon name="chevron" width="18" height="18" /></summary><p>{item.description}</p></details>)}</div> : <p className="results-muted">표시할 항목이 없어요. 문제가 없다는 판단을 뜻하지는 않아요.</p>}</Card>
          <Card title="쉬운 설명" description="표시 방식만 확인하는 설명 예시예요.">{visibleExplanation ? <p className="result-explanation">{visibleExplanation}</p> : <div className="result-fallback"><Icon name="info" /><p>{result.sources.length ? '설명을 불러오지 못했어요. 샘플 계산값과 연결된 공식 자료를 직접 확인해 주세요.' : '근거가 연결되지 않아 설명을 표시하지 않아요. 실제 확인은 공식 자료나 상담을 통해 진행해 주세요.'}</p></div>}</Card>
        </div><Card title="공식 자료 예시" description="공식 자료의 표시 예시예요. 내 문서에 맞춰 검색한 결과가 아니에요." action={<Badge>참고 원문</Badge>}>
          {result.sources.length ? <div className="source-list">{result.sources.map(source => { const href = safeOfficialUrl(source.url); return <article className="source-card" key={source.id}><span className="source-card__label">공식 원문 · 참고 예시</span><h3>{source.title}</h3>{source.snippet && <p>{source.snippet}</p>}{href ? <a href={href} target="_blank" rel="noreferrer" className="source-link">공식 원문 열기<span className="sr-only">: {source.title} (새 탭)</span></a> : <p className="source-missing">원문 링크를 확인할 수 없어요.</p>}</article> })}</div> : <div className="source-empty"><Icon name="file" width="28" height="28" /><h3>연결된 근거가 없어요</h3><p>출처를 임의로 만들지 않아요. 실제 판단은 공식 확인이 필요해요.</p></div>}
        </Card></div>
        <div className="results-actions"><p>추가로 확인하고 싶은 내용이 있나요?</p><Button onClick={onAsk}><Icon name="chat" width="18" height="18" />이 결과에 대해 질문하기</Button></div>
      </>}
    </div>
    <aside className="consultation" aria-labelledby="consultation-title"><Icon name="info" /><div><h2 id="consultation-title">정확한 확인이 필요하다면</h2><p>{result.disclaimer}</p><div className="consultation-links"><a href="tel:1350">고용노동부 1350</a><a href="tel:132">대한법률구조공단 132</a></div></div></aside>
  </>
}
