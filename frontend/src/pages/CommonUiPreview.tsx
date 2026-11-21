import { useEffect, useRef, useState } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Checkbox, InputField, SelectField } from '../components/common/FormControls'
import { Badge, StatePanel } from '../components/common/Status'
import { Icon } from '../components/common/Icon'
import './preview.css'

type PreviewState = 'empty' | 'loading' | 'error'

export function CommonUiPreview() {
  const [language, setLanguage] = useState('ko')
  const [name, setName] = useState('')
  const [consent, setConsent] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [state, setState] = useState<PreviewState>('empty')
  const nameRef = useRef<HTMLInputElement>(null)
  const error = submitted && !name.trim() ? '문서 이름을 입력해 주세요.' : undefined
  useEffect(() => {
    if (error) nameRef.current?.focus()
  }, [error])

  return <>
    <div className="page-heading"><div><p className="eyebrow">SAVER WORKSPACE</p><h1>작은 확인이, 든든한 시작이 되도록</h1><p>내 문서를 이해하고 권리를 확인하는 공간을 준비하고 있어요.</p></div><span className="heading-icon"><Icon name="shield" width="30" height="30" /></span></div>
    <div className="preview-notice"><Icon name="info" /><p><strong>공통 UI 미리보기</strong><span>메뉴와 입력 요소를 눌러보세요. 표시된 내용은 예시이며 문서가 업로드되거나 저장되지 않아요.</span></p></div>
    <div className="preview-grid">
      <Card title="익숙한 언어로 시작해요" description="입력창 · 선택창 · 동의 체크" action={<Badge>입력 요소</Badge>}>
        <form onSubmit={event => { event.preventDefault(); setSubmitted(true) }} noValidate>
          <div className="form-stack">
            <SelectField label="안내받을 언어" value={language} onChange={event => setLanguage(event.target.value)} hint="선택 상태를 확인하는 미리보기예요. 실제 번역은 추후 제공돼요."><option value="ko">한국어 · Korean</option><option value="en">English · 영어</option><option value="vi">Tiếng Việt · 베트남어</option><option value="zh-CN">中文 · 중국어</option></SelectField>
            <InputField ref={nameRef} label="문서 이름" placeholder="예: 첫 아르바이트 근로계약서" value={name} onChange={event => { setName(event.target.value); setSubmitted(false) }} required maxLength={100} error={error} hint="알아보기 쉬운 이름을 입력해 보세요." />
            <InputField label="문서 종류" value="근로계약서" disabled hint="비활성화된 입력창 예시예요." />
          </div>
          <div className="form-consent"><Checkbox label="문서 처리 및 개인정보 안내를 확인했습니다." checked={consent} onChange={event => { setConsent(event.target.checked); setSubmitted(false) }} /></div>
          <div className="form-actions"><p role="status">{submitted && name.trim() ? '입력 상태를 확인했어요. 실제 문서는 저장되지 않았어요.' : '동의하면 입력 확인 버튼을 사용할 수 있어요.'}</p><Button type="submit" disabled={!consent}>입력 확인하기</Button></div>
        </form>
      </Card>
      <div className="preview-stack">
        <Card title="상태를 한눈에 확인해요" description="색상과 문구로 상태를 함께 표시해요."><div className="badge-row"><Badge tone="success">확인 완료</Badge><Badge tone="warning">확인 필요</Badge><Badge>아직 입력하지 않음</Badge></div><div className="example-result"><span className="example-result__icon"><Icon name="file" width="24" height="24" /></span><div><strong>근로계약서</strong><p>내용을 확인하면 다음 단계로 이어져요.</p></div><Badge>예시</Badge></div></Card>
        <Card title="다음 행동을 명확하게" description="기본 · 보조 · 비활성 · 처리 중 버튼"><div className="button-examples"><Button onClick={() => setState('loading')}>내용 확인하기</Button><Button variant="secondary" onClick={() => setState('empty')}>다시 선택</Button><Button variant="ghost" onClick={() => setState('error')}>오류 상태 보기</Button><Button disabled>준비 중</Button><Button loading>확인하는 중</Button></div></Card>
      </div>
    </div>
    <Card title="기다리는 순간에도 알기 쉽게" description="내용이 없거나, 처리 중이거나, 다시 시도해야 할 때" className="state-card">
      <div className="state-switch" role="group" aria-label="표시할 상태">{([{ id: 'empty', label: '빈 화면' }, { id: 'loading', label: '로딩' }, { id: 'error', label: '오류' }] as const).map(item => <button type="button" key={item.id} aria-pressed={state === item.id} onClick={() => setState(item.id)}>{item.label}</button>)}</div>
      <StatePanel status={state}
        title={state === 'empty' ? '아직 확인한 문서가 없어요' : state === 'loading' ? '문서 내용을 확인하고 있어요' : '내용을 불러오지 못했어요'}
        description={state === 'empty' ? '문서를 올리면 이곳에서 추출된 내용과 점검 결과를 확인할 수 있어요.' : state === 'loading' ? '처리 중 상태 예시예요. 다른 상태를 선택해 미리보기를 바꿀 수 있어요.' : '오류 상태 예시예요. 다시 시도하면 기본 화면으로 돌아가요.'}
        action={state === 'error' ? <Button variant="secondary" onClick={() => setState('empty')}>다시 시도</Button> : undefined} />
    </Card>
  </>
}
