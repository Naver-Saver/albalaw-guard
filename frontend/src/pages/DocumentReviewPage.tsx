import { useEffect, useRef, useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Checkbox, InputField } from '../components/common/FormControls'
import { Badge } from '../components/common/Status'
import { Icon } from '../components/common/Icon'
import { WEEKDAYS, canConfirmReview, editReviewSession, toReviewRequest, validateReviewDraft } from '../features/document-review/model'
import type { ReviewDraft, ReviewRequest, ReviewSession } from '../features/document-review/model'
import { useObjectUrl } from '../features/document-upload/useObjectUrl'
import { createPreviewBlob } from '../features/document-upload/previewBlob'
import './review.css'

export function DocumentReviewPage({ session, onChange, onReplace, onConfirm }: { session: ReviewSession; onChange: (session: ReviewSession) => void; onReplace: () => void; onConfirm: (request: ReviewRequest) => void }) {
  const { draft, ocr } = session
  const errors = validateReviewDraft(draft)
  const { url, setPreviewFile } = useObjectUrl()
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [zoomed, setZoomed] = useState(false)
  const [notice, setNotice] = useState('')
  const imageFailed = Boolean(url && failedUrl === url)
  const ready = canConfirmReview(session) && !imageFailed
  const wageRef = useRef<HTMLInputElement>(null)
  const hoursRef = useRef<HTMLInputElement>(null)
  const breakRef = useRef<HTMLInputElement>(null)
  const yearRef = useRef<HTMLInputElement>(null)
  const consentRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setPreviewFile(session.document ? createPreviewBlob(session.document.file, session.document.kind) : null)
  }, [session.document, setPreviewFile])

  function update(patch: Partial<ReviewDraft>) {
    onChange(editReviewSession(session, { ...draft, ...patch }))
    setNotice('')
  }

  function fieldBadge(field: keyof Omit<ReviewDraft, 'year'>) {
    const changed = JSON.stringify(draft[field]) !== JSON.stringify(session.initialDraft[field])
    if (changed) return <Badge tone="success">직접 수정</Badge>
    if (!ocr) return <Badge>직접 입력</Badge>
    return ocr.extracted[field].confidence === 'low' ? <Badge tone="warning">확인 필요</Badge> : <Badge>추출된 값</Badge>
  }

  function sourceHint(field: keyof Omit<ReviewDraft, 'year'>, fallback: string) {
    return ocr?.extracted[field].source_text ? `${session.mode === 'sample' ? '샘플 원문' : 'OCR 원문'}: ${ocr.extracted[field].source_text}` : fallback
  }

  return <>
    <div className="review-heading"><div><p className="eyebrow">CHECK BEFORE YOU CONTINUE</p><h1>{ocr ? '추출한 내용이 맞는지 확인해 주세요' : '원본을 보며 내용을 입력해 주세요'}</h1><p>시급과 근무조건을 확인하고, 잘못되거나 비어 있는 항목을 수정해 주세요.</p></div><Badge>STEP 02 · 내용 확인</Badge></div>
    <div className="review-notice"><Icon name="info" /><p><strong>{session.mode === 'sample' ? '샘플 OCR 응답 체험' : ocr ? 'OCR 추출 완료 · 직접 확인 필요' : '직접 입력'}</strong>{session.mode === 'sample' ? '아래 문서와 값은 모두 화면 체험을 위한 샘플이에요. 업로드한 문서에서 읽은 값이 아니에요.' : ocr ? '서버에서 읽어낸 값이에요. 인식 오류나 누락이 있을 수 있으니 원본과 비교해 주세요.' : '원본을 보고 직접 입력해 주세요.'}</p></div>
    <div className="review-grid">
      <Card title="원본 문서" description="원본과 오른쪽 입력 내용을 비교해 주세요." action={<Badge>{session.mode === 'sample' ? '샘플' : session.document?.docType === 'payslip' ? '급여명세서' : '근로계약서'}</Badge>}>
        <div className="review-original">
          {session.mode === 'sample' ? <article className={`sample-contract ${zoomed ? 'sample-contract--zoomed' : ''}`} aria-label="화면 체험용 샘플 근로계약서"><span className="sample-contract__label">화면 체험용 예시 · 실제 계약서 아님</span><h2>근로계약서</h2><p className="sample-contract__intro">아래 근로조건을 함께 확인합니다.</p><dl><div><dt>시급</dt><dd>10,000원</dd></div><div><dt>근무요일</dt><dd>월요일 ~ 금요일</dd></div><div><dt>주 근무시간</dt><dd>20시간</dd></div><div className="sample-contract__missing"><dt>휴게시간</dt><dd>미기재</dd></div></dl><p className="sample-contract__foot">실제 문서와 내용이 다를 수 있습니다.</p></article> : session.document?.kind === 'image' ? url && !imageFailed ? <img className={zoomed ? 'review-image review-image--zoomed' : 'review-image'} src={url} alt="업로드한 문서 원본" onError={() => { setFailedUrl(url); onChange({ ...session, confirmed: false }) }} /> : <p className="review-empty-original" role="status">{imageFailed ? '원본 이미지를 표시할 수 없어요. 다른 문서로 교체해 주세요.' : '원본 미리보기를 준비하고 있어요.'}</p> : <div className="review-pdf"><Icon name="file" width="36" height="36" /><strong>{session.document?.file.name ?? '원본 문서 없음'}</strong><p>PDF 원본은 새 탭에서 열고 입력 내용과 비교해 주세요.</p>{url && <a className="button button--secondary" href={url} target="_blank" rel="noreferrer">PDF 원본 열기</a>}</div>}
        </div>
        <div className="review-original-actions">{(session.mode === 'sample' || session.document?.kind === 'image' && !imageFailed) && <Button variant="secondary" aria-pressed={zoomed} onClick={() => setZoomed(!zoomed)}>{zoomed ? '기본 크기로 보기' : '확대해서 보기'}</Button>}<Button variant="ghost" onClick={onReplace}>다른 문서로 교체</Button></div>
        {session.document && <p className="review-file-name">{session.document.file.name}</p>}
        {ocr && <details className="review-raw"><summary>{session.mode === 'sample' ? '샘플 OCR 원문 보기' : 'OCR 원문 보기'}</summary><pre>{ocr.raw_text}</pre></details>}
      </Card>
      <Card title={ocr ? '추출된 내용' : '확인할 내용'} description="확인한 값 전체를 다음 단계의 입력값으로 사용해요.">
        <form noValidate onSubmit={event => {
          event.preventDefault()
          if (!ready) {
            setNotice('입력값과 원본 확인 동의를 확인해 주세요.')
            ;(errors.hourly_wage ? wageRef : errors.weekly_hours ? hoursRef : errors.break_minutes ? breakRef : errors.year ? yearRef : consentRef).current?.focus()
            return
          }
          onConfirm(toReviewRequest(session))
        }}>
          <div className="review-fields">
            <div className="review-field"><div className="review-field__badge">{fieldBadge('hourly_wage')}</div><InputField ref={wageRef} label="시급 (원)" inputMode="numeric" value={draft.hourly_wage} onChange={event => update({ hourly_wage: event.target.value })} error={errors.hourly_wage} hint={sourceHint('hourly_wage', '문서에 적힌 시급을 원 단위로 입력해 주세요.')} required /></div>
            <div className="review-field"><div className="review-field__badge">{fieldBadge('weekly_hours')}</div><InputField ref={hoursRef} label="주 소정근로시간 (시간)" inputMode="decimal" value={draft.weekly_hours} onChange={event => update({ weekly_hours: event.target.value })} error={errors.weekly_hours} hint={sourceHint('weekly_hours', '주 단위 근무시간을 입력해 주세요. 예: 20, 25.5')} required /></div>
            <fieldset className="review-days"><legend>근무요일 (선택)</legend><div className="review-days__badge">{fieldBadge('work_days')}</div><div className="review-days__options">{WEEKDAYS.map(day => <label key={day}><input type="checkbox" checked={draft.work_days.includes(day)} onChange={event => update({ work_days: event.target.checked ? WEEKDAYS.filter(value => value === day || draft.work_days.includes(value)) : draft.work_days.filter(value => value !== day) })} /><span>{day}</span></label>)}</div><p>{sourceHint('work_days', '문서에 근무요일이 적혀 있다면 선택해 주세요.')}</p>{errors.work_days && <p className="field__hint--error">{errors.work_days}</p>}</fieldset>
            <div className="review-field"><div className="review-field__badge">{fieldBadge('break_minutes')}</div><InputField ref={breakRef} label="하루 휴게시간 (분, 선택)" inputMode="numeric" value={draft.break_minutes} onChange={event => update({ break_minutes: event.target.value })} error={errors.break_minutes} hint={sourceHint('break_minutes', '문서에 없거나 확실하지 않다면 비워 두세요. 0분과 미입력은 구분해요.')} /></div>
            <InputField ref={yearRef} label="적용 연도" inputMode="numeric" value={draft.year} onChange={event => update({ year: event.target.value })} error={errors.year} hint="문서에 적용되는 연도를 확인해 주세요." required />
          </div>
          <div className="review-confirm"><Checkbox ref={consentRef} label="원본과 입력 내용을 비교하고, 맞는지 확인했습니다." checked={session.confirmed} disabled={imageFailed} onChange={event => onChange({ ...session, confirmed: event.target.checked })} /><p>내용을 바꾸면 확인 동의가 초기화돼요. 수정 후 다시 확인해 주세요.</p></div>
          <Button type="submit" className="review-submit" disabled={!ready}>{session.mode === 'sample' ? '수정 내용으로 점검 (체험)' : '확인한 내용으로 점검하기'}</Button><p className="review-submit-hint">{session.mode === 'sample' ? '실제 점검 요청은 전송하지 않아요. 확인한 입력값만 다음 화면에서 보여줘요.' : '확인한 입력값을 서버로 전송해 계산과 설명을 요청해요.'}</p><div role="alert">{notice}</div>
        </form>
      </Card>
    </div>
  </>
}
