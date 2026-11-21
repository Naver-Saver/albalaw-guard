import { useRef, useState } from 'react'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Status'
import { Card } from '../components/common/Card'
import { validateRecording } from '../features/recordings/validation'
import './recordings.css'

const entries = [
  { time: '00:12', speaker: 'A', category: '임금', text: '이번 달부터 시급을 조정할게요.' },
  { time: '01:05', speaker: 'B', category: '근무시간', text: '다음 주 근무시간을 확인하고 싶어요.' },
  { time: '01:30', speaker: 'A', category: '기타', text: '확인한 뒤 다시 알려드릴게요.' },
] as const

export function RecordingsPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [consent, setConsent] = useState(false)
  const [showSample, setShowSample] = useState(false)
  const [showOther, setShowOther] = useState(false)
  const [names, setNames] = useState({ A: '화자 A', B: '화자 B' })

  function selectFile(next: File | undefined) {
    setShowSample(false)
    setConsent(false)
    if (!next) { setFile(null); setError(''); return }
    const problem = validateRecording(next)
    setFile(problem ? null : next)
    setError(problem ?? '')
  }
  function clearFile() {
    selectFile(undefined)
    if (inputRef.current) inputRef.current.value = ''
  }
  return <div className="recordings-page">
    <header className="recordings-heading"><div><p className="eyebrow">YOUR CONVERSATION</p><h1>대화 기록을 정리해 보세요</h1><p>녹음 파일을 선택하고 대화 정리 화면을 체험할 수 있어요.</p></div><Badge>대화 기록 체험</Badge></header>
    <div className="recordings-notice"><strong>실제 파일은 전송하거나 분석하지 않아요</strong><p>아래 타임라인은 선택한 파일과 관계없는 고정 샘플이에요. 녹음할 때는 상대방의 동의와 개인정보 보호를 고려해 주세요.</p></div>
    <div className="recordings-layout"><div className="recordings-column">
      <Card title="녹음 파일 선택" description="m4a, mp3, wav · 최대 200MB"><label className="recordings-file" htmlFor="recording-file">녹음 파일 선택하기</label><input ref={inputRef} id="recording-file" type="file" accept=".m4a,.mp3,.wav,audio/mp4,audio/mpeg,audio/wav" onChange={event => selectFile(event.target.files?.[0])} />{error && <p className="recordings-error" role="alert">{error}</p>}{file && <div className="recordings-selected"><span>{file.name}</span><Button variant="ghost" onClick={clearFile}>삭제</Button></div>}<p className="recordings-hint">길이 제한은 정해지는 대로 안내할게요. 현재는 파일 길이를 검사하지 않아요.</p><label className="recordings-consent"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />녹음 내용에 개인정보가 포함될 수 있음을 확인했어요.</label><div className="recordings-actions"><Button disabled={!file || !consent} onClick={() => setShowSample(true)}>샘플 결과 보기</Button><Button variant="secondary" onClick={() => setShowSample(true)}>파일 없이 샘플 보기</Button></div></Card>
      <Card title="화자 이름" description="화면에서만 이름을 바꿀 수 있어요."><div className="speaker-fields">{(['A', 'B'] as const).map(id => <label key={id}>화자 {id}<input value={names[id]} maxLength={30} onChange={event => setNames(previous => ({ ...previous, [id]: event.target.value }))} /></label>)}</div></Card>
    </div><div className="recordings-column"><Card title="대화 타임라인" description="시각과 분류별 핵심 발언을 확인해 보세요." action={showSample ? <Badge>고정 샘플</Badge> : undefined}>
      {!showSample ? <div className="recordings-empty"><p>아직 표시할 내용이 없어요.</p><p>샘플 결과를 열어 대화 정리 화면을 살펴보세요.</p></div> : <><label className="recordings-filter"><input type="checkbox" checked={showOther} onChange={event => setShowOther(event.target.checked)} />기타 항목 보기</label><ol className="recordings-timeline">{entries.filter(entry => showOther || entry.category !== '기타').map(entry => <li key={entry.time}><div><time>{entry.time}</time><Badge>{entry.category}</Badge></div><strong>{names[entry.speaker].trim() || `화자 ${entry.speaker}`}</strong><p>{entry.text}</p></li>)}</ol><details className="recordings-transcript"><summary>샘플 전체 대본 보기</summary>{entries.map(entry => <p key={entry.time}>{entry.time} · {names[entry.speaker].trim() || `화자 ${entry.speaker}`} : {entry.text}</p>)}</details></>}
    </Card></div></div>
  </div>
}
