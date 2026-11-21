import { useEffect, useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Checkbox, InputField } from '../components/common/FormControls'
import { Badge } from '../components/common/Status'
import { Icon } from '../components/common/Icon'
import { useObjectUrl } from '../features/document-upload/useObjectUrl'
import { createPreviewBlob } from '../features/document-upload/previewBlob'
import { toPayslipRequest, validatePayslipDraft } from '../features/payslip/model'
import type { PayslipDraft, PayslipLineDraft, PayslipRequest, PayslipSession } from '../features/payslip/model'
import './review.css'

type ListKey = 'items' | 'deductions'

export function PayslipReviewPage({ session, onChange, onReplace, onConfirm }: { session: PayslipSession; onChange: (session: PayslipSession) => void; onReplace: () => void; onConfirm: (request: PayslipRequest) => void }) {
  const { draft } = session
  const errors = validatePayslipDraft(draft)
  const ready = session.confirmed && Object.keys(errors).length === 0
  const { url, setPreviewFile } = useObjectUrl()
  const [notice, setNotice] = useState('')
  useEffect(() => { setPreviewFile(createPreviewBlob(session.document.file, session.document.kind)) }, [session.document, setPreviewFile])

  function update(patch: Partial<PayslipDraft>) { onChange({ ...session, draft: { ...draft, ...patch }, confirmed: false }); setNotice('') }
  function updateLine(key: ListKey, index: number, patch: Partial<PayslipLineDraft>) { update({ [key]: draft[key].map((line, i) => (i === index ? { ...line, ...patch } : line)) }) }
  const auto = (key: keyof PayslipDraft) => draft[key] !== '' && JSON.stringify(draft[key]) === JSON.stringify(session.initialDraft[key])

  const lineList = (key: ListKey, title: string) => <fieldset className="payslip-lines">
    <legend>{title}</legend>
    {draft[key].map((line, index) => <div className="payslip-line" key={index}>
      <InputField label={`${title} ${index + 1} 이름`} value={line.name} onChange={event => updateLine(key, index, { name: event.target.value })} hint={line.source ? `문서에서 읽은 부분: “${line.source}”` : undefined} />
      <InputField label="금액 (원)" inputMode="numeric" value={line.amount} onChange={event => updateLine(key, index, { amount: event.target.value })} />
      <Button variant="ghost" aria-label={`${title} ${index + 1} 삭제`} onClick={() => update({ [key]: draft[key].filter((_, i) => i !== index) })}>삭제</Button>
    </div>)}
    <Button variant="secondary" onClick={() => update({ [key]: [...draft[key], { name: '', amount: '' }] })}>{title} 추가</Button>
    {errors[key] && <p className="field__hint--error">{errors[key]}</p>}
  </fieldset>

  return <>
    <div className="review-heading"><div><p className="eyebrow">CHECK YOUR PAYSLIP</p><h1>급여명세서에서 읽은 내용을 확인해 주세요</h1><p>문서에서 읽은 항목과 금액이 입력란에 들어가 있어요. 원본과 다르면 고쳐 주세요.</p></div><Badge>STEP 02 · 내용 확인</Badge></div>
    <div className="review-notice"><Icon name="info" /><p><strong>OCR 추출 완료 · 직접 확인 필요</strong>지급·공제 항목, 합계는 자동으로 채웠어요. 인식 오류나 누락이 있을 수 있어요.</p></div>
    <div className="review-grid">
      <Card title="원본 문서" description="원본과 오른쪽 입력 내용을 비교해 주세요." action={<Badge>급여명세서</Badge>}>
        <div className="review-original">{session.document.kind === 'image' ? url ? <img className="review-image" src={url} alt="업로드한 급여명세서 원본" /> : <p className="review-empty-original">원본 미리보기를 준비하고 있어요.</p> : <div className="review-pdf"><Icon name="file" width="36" height="36" /><strong>{session.document.file.name}</strong>{url && <a className="button button--secondary" href={url} target="_blank" rel="noreferrer">PDF 원본 열기</a>}</div>}</div>
        <div className="review-original-actions"><Button variant="ghost" onClick={onReplace}>다른 문서로 교체</Button></div>
        <details className="review-raw"><summary>OCR 원문 보기</summary><pre>{session.rawText}</pre></details>
      </Card>
      <Card title="추출된 내용" description="확인한 값으로 검산·누락 항목·최저임금을 점검해요.">
        <form noValidate onSubmit={event => { event.preventDefault(); if (!ready) { setNotice('입력값과 원본 확인 동의를 확인해 주세요.'); return } onConfirm(toPayslipRequest(session)) }}>
          <div className="review-fields">
            {lineList('items', '지급 항목')}
            {lineList('deductions', '공제 항목')}
            <div className="review-field"><div className="review-field__badge">{auto('total_pay') ? <Badge>자동 입력됨</Badge> : <Badge>직접 입력</Badge>}</div><InputField label="지급총액 (원, 선택)" inputMode="numeric" value={draft.total_pay} onChange={event => update({ total_pay: event.target.value })} error={errors.total_pay} hint="명세서에 적힌 합계를 그대로 입력하면 항목 합과 비교해요." /></div>
            <div className="review-field"><div className="review-field__badge">{auto('net_pay') ? <Badge>자동 입력됨</Badge> : <Badge>직접 입력</Badge>}</div><InputField label="실지급액 (원, 선택)" inputMode="numeric" value={draft.net_pay} onChange={event => update({ net_pay: event.target.value })} error={errors.net_pay} /></div>
            <InputField label="임금지급일 (선택)" value={draft.pay_date} onChange={event => update({ pay_date: event.target.value })} hint={auto('pay_date') ? '문서에서 읽은 값이에요.' : undefined} />
            <InputField label="근로자 이름 (선택)" value={draft.employee_name} onChange={event => update({ employee_name: event.target.value })} hint="명세서에 적혀 있는지만 확인하고 저장하지 않아요." />
            <InputField label="계산방법 (선택)" value={draft.calculation_method} onChange={event => update({ calculation_method: event.target.value })} />
            <InputField label="시급 (원, 알면 입력)" inputMode="numeric" value={draft.hourly_wage} onChange={event => update({ hourly_wage: event.target.value })} error={errors.hourly_wage} hint="입력하면 최저임금과 주휴수당도 함께 확인해요." />
            <InputField label="주 소정근로시간 (알면 입력)" inputMode="decimal" value={draft.weekly_hours} onChange={event => update({ weekly_hours: event.target.value })} error={errors.weekly_hours} />
            <InputField label="적용 연도" inputMode="numeric" value={draft.year} onChange={event => update({ year: event.target.value })} error={errors.year} required />
          </div>
          <div className="review-confirm"><Checkbox label="원본과 입력 내용을 비교하고, 맞는지 확인했습니다." checked={session.confirmed} onChange={event => onChange({ ...session, confirmed: event.target.checked })} /><p>내용을 바꾸면 확인 동의가 초기화돼요.</p></div>
          <Button type="submit" className="review-submit" disabled={!ready}>확인한 내용으로 점검하기</Button><div role="alert">{notice}</div>
        </form>
      </Card>
    </div>
  </>
}
