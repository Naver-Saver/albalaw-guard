import { useState } from 'react'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Status'
import './question.css'

export function QuestionPage({ onBack }: { onBack?: () => void }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<string[]>([])
  function submit() {
    const trimmed = question.trim()
    if (!trimmed) return
    setMessages(previous => [...previous, trimmed])
    setQuestion('')
  }
  return <section className="question-page" aria-labelledby="question-title">
    <header className="question-header"><div><p className="eyebrow">ASK SAVER</p><h1 id="question-title">궁금한 점을 물어보세요</h1><p>일하면서 궁금했던 내용을 편하게 적어 보세요.</p></div><Badge>질문 화면 체험</Badge></header>
    <div className="question-notice"><strong>샘플 화면이에요</strong><p>입력한 질문은 전송되지 않으며 아래 안내는 고정된 예시예요. 실제 답변과 음성 기능은 준비 중이에요.</p></div>
    <div className="question-conversation" aria-live="polite" aria-relevant="additions">
      <div className="question-message question-message--assistant"><strong>Saver</strong><p>안녕하세요! 근로계약서, 급여, 근무시간에 대해 궁금한 점을 적어 보세요.</p><span>예시 안내</span></div>
      {messages.map((message, index) => <div className="question-exchange" key={index}><div className="question-message question-message--user"><strong>나</strong><p>{message}</p></div><div className="question-message question-message--assistant"><strong>Saver · 예시 안내</strong><p>질문해 주셔서 고마워요. 현재는 실제 답변을 제공하지 않는 체험 화면이에요. 정확한 내용은 고용노동부 1350 또는 대한법률구조공단 132에 문의해 주세요.</p><span>입력 내용에 따른 답변이 아니에요</span></div></div>)}
    </div>
    <div className="question-suggestions"><p>이런 질문을 해 볼 수 있어요</p>{['주휴수당을 받을 수 있나요?', '급여명세서는 꼭 받아야 하나요?', '휴게시간은 얼마나 주어지나요?'].map(item => <button type="button" key={item} onClick={() => setQuestion(item)}>{item}</button>)}</div>
    <form className="question-form" onSubmit={event => { event.preventDefault(); submit() }}><label htmlFor="question-input">질문 입력</label><div><textarea id="question-input" value={question} maxLength={1000} onChange={event => setQuestion(event.target.value)} placeholder="궁금한 내용을 입력해 주세요" rows={3} /><Button type="submit" disabled={!question.trim()}>질문하기</Button></div><p>음성 질문은 준비 중이에요. 지금은 텍스트로 화면을 체험할 수 있어요.</p></form>
    <div className="question-footer">{onBack && <Button variant="secondary" onClick={onBack}>샘플 결과로 돌아가기</Button>}<p>이 화면은 법률 자문을 제공하지 않아요. <a href="tel:1350">고용노동부 1350</a> · <a href="tel:132">대한법률구조공단 132</a></p></div>
  </section>
}
