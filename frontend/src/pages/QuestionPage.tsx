import { useEffect, useRef, useState } from 'react'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Status'
import { askText, validateQuestion } from '../features/questions/client'
import type { AskResult } from '../features/questions/client'
import { safeOfficialUrl } from '../features/check-results/sourceUrl'
import { AnswerBody } from '../components/AnswerBody'
import { SourceDetail } from '../components/SourceDetail'
import type { Language } from '../features/document-upload/validation'
import './question.css'
import { VoiceQuestion } from '../components/VoiceQuestion'

const routeLabels = { faq: 'FAQ · CLOVA Chatbot', studio: '근거 기반 · CLOVA Studio', none: '상담·추가 확인 안내' }

export function QuestionPage({ onBack, language = 'ko' }: { onBack?: () => void; language?: Language }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<{ question: string; result: AskResult }[]>([])
  const [pending, setPending] = useState('')
  const [error, setError] = useState('')
  const [voiceBusy, setVoiceBusy] = useState(false)
  const controllerRef = useRef<AbortController | null>(null)
  const fieldRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => () => controllerRef.current?.abort(), [])

  async function submit() {
    if (controllerRef.current || voiceBusy) return
    const trimmed = question.trim()
    const invalid = validateQuestion(trimmed)
    if (invalid) { setError(invalid); fieldRef.current?.focus(); return }
    const controller = new AbortController()
    controllerRef.current = controller
    setError(''); setPending(trimmed)
    try {
      const result = await askText(trimmed, controller.signal)
      if (!controller.signal.aborted) {
        setMessages(previous => [...previous, { question: trimmed, result }])
        setQuestion('')
      }
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '답변을 가져오지 못했어요. 다시 시도해 주세요.')
    } finally {
      if (controllerRef.current === controller) { controllerRef.current = null; setPending('') }
    }
  }
  function cancel() {
    controllerRef.current?.abort(); controllerRef.current = null; setPending('')
  }
  return <section className="question-page" aria-labelledby="question-title">
    <header className="question-header"><div><p className="eyebrow">ASK SAVER</p><h1 id="question-title">궁금한 점을 물어보세요</h1><p>일하면서 궁금했던 내용을 편하게 적어 보세요.</p></div><Badge>텍스트 · 음성 질문</Badge></header>
    <div className="question-notice"><strong>질문을 서버로 보내 답변을 받아요</strong><p>이름·주소·계좌 같은 개인정보는 입력하지 마세요. 선택한 언어로 번역해 보여주고, 답변을 소리로 들을 수 있어요. 법률 자문을 대신하지 않아요.</p></div>
    <div className="question-conversation" aria-live="polite" aria-relevant="additions">
      {!messages.length && !pending && <div className="question-message question-message--assistant"><strong>Saver</strong><p>근로계약서, 급여, 근무시간에 대해 궁금한 점을 적어 보세요.</p></div>}
      {messages.map((message, index) => <div className="question-exchange" key={index}><div className="question-message question-message--user"><strong>나</strong><p>{message.question}</p></div><div className="question-message question-message--assistant"><strong>Saver</strong><p><Badge>{routeLabels[message.result.route]}</Badge></p><AnswerBody answer={message.result.answer} language={language} />{message.result.sources.length ? <details><summary>답변 근거 보기</summary>{message.result.sources.map(source => { const href = safeOfficialUrl(source.url); return <article key={source.id}><h3>{source.title}</h3>{source.snippet && <p>{source.snippet}</p>}<SourceDetail id={source.id} />{href ? <a href={href} target="_blank" rel="noreferrer">공식 원문 열기 (새 탭)</a> : <p>원문 링크를 확인할 수 없어요.</p>}</article> })}</details> : <p>연결된 근거가 없어요. 고용노동부 1350 또는 법률구조공단 132에 확인해 주세요.</p>}</div></div>)}
    </div>
    {pending && <div role="status"><p>{pending}</p><p>답변을 확인하고 있어요.</p><Button variant="secondary" onClick={cancel}>요청 취소</Button></div>}
    <div className="question-suggestions"><p>이런 질문을 해 볼 수 있어요</p>{['주휴수당을 받을 수 있나요?', '급여명세서는 꼭 받아야 하나요?', '휴게시간은 얼마나 주어지나요?'].map(item => <button type="button" disabled={!!pending || voiceBusy} key={item} onClick={() => { setQuestion(item); setError(''); fieldRef.current?.focus() }}>{item}</button>)}</div>
    <form className="question-form" onSubmit={event => { event.preventDefault(); void submit() }}><label htmlFor="question-input">질문 입력</label><div><textarea ref={fieldRef} id="question-input" value={question} disabled={!!pending || voiceBusy} aria-invalid={!!error} aria-describedby="question-help question-error" onChange={event => { setQuestion(event.target.value); setError('') }} placeholder="궁금한 내용을 입력해 주세요" rows={3} /><Button type="submit" disabled={!!pending || voiceBusy || !!validateQuestion(question)} loading={!!pending}>질문하기</Button></div><p id="question-help">2~300자 · {Array.from(question.trim()).length}/300 · 한국어로 질문해 주세요.</p><p id="question-error" role="alert">{error}</p>{error && <Button variant="secondary" onClick={() => void submit()}>같은 질문 다시 시도</Button>}</form>
    <VoiceQuestion disabled={!!pending} onBusy={setVoiceBusy} onResult={result => setMessages(previous => [...previous, { question: result.question || "(인식된 음성 없음)", result }])} />
    <div className="question-footer">{onBack && <Button variant="secondary" onClick={onBack}>점검 결과로 돌아가기</Button>}<p>이 화면은 법률 자문을 제공하지 않아요. <a href="tel:1350">고용노동부 1350</a> · <a href="tel:132">대한법률구조공단 132</a></p></div>
  </section>
}
