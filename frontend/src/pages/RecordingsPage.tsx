import { useEffect, useRef, useState } from 'react'
import { Button } from '../components/common/Button'
import { Badge, StatePanel } from '../components/common/Status'
import { Card } from '../components/common/Card'
import { SourceDetail } from '../components/SourceDetail'
import { validateRecording } from '../features/recordings/validation'
import { createRecording, findTimelineEvidence, formatClock, pollRecording } from '../features/recordings/client'
import type { RecordingJob, TimelineEntry, TimelineEvidence } from '../features/recordings/client'
import { safeOfficialUrl } from '../features/check-results/sourceUrl'
import type { Language } from '../features/document-upload/validation'
import './recordings.css'

const SAMPLE: TimelineEntry[] = [
  { start_ms: 12_000, speaker: 'A', category: '임금', text: '이번 달부터 시급을 조정할게요.' },
  { start_ms: 65_000, speaker: 'B', category: '근무시간', text: '다음 주 근무시간을 확인하고 싶어요.' },
  { start_ms: 90_000, speaker: 'A', category: '기타', text: '확인한 뒤 다시 알려드릴게요.' },
]
const statusText = { queued: '대기 중', processing: '음성을 글로 바꾸고 대화를 정리하고 있어요', done: '완료', failed: '실패' } as const

export function RecordingsPage({ language = 'ko' }: { language?: Language }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [consent, setConsent] = useState(false)
  const [job, setJob] = useState<RecordingJob | null>(null)
  const [sample, setSample] = useState(false)
  const [busy, setBusy] = useState(false)
  const [showOther, setShowOther] = useState(false)
  const [names, setNames] = useState<Record<string, string>>({})
  const [evidence, setEvidence] = useState<TimelineEvidence | null>(null)
  const [evidenceBusy, setEvidenceBusy] = useState(false)
  useEffect(() => () => controllerRef.current?.abort(), [])

  const timeline = sample ? SAMPLE : job?.status === 'done' ? job.timeline : []
  const speakers = sample ? ['A', 'B'] : job?.speakers?.length ? job.speakers : [...new Set(timeline.map(e => e.speaker))]
  const defaultName = (id: string) => (id.startsWith('화자') ? id : `화자 ${id}`)
  const nameOf = (id: string) => names[id]?.trim() || defaultName(id)

  function resetResult() { controllerRef.current?.abort(); controllerRef.current = null; setJob(null); setSample(false); setEvidence(null); setBusy(false) }
  function selectFile(next: File | undefined) {
    resetResult(); setConsent(false)
    if (!next) { setFile(null); setError(''); return }
    const problem = validateRecording(next)
    setFile(problem ? null : next); setError(problem ?? '')
  }
  function clearFile() { selectFile(undefined); if (inputRef.current) inputRef.current.value = '' }

  async function start() {
    if (!file || !consent || busy) return
    resetResult()
    const controller = new AbortController()
    controllerRef.current = controller
    setBusy(true); setError('')
    try {
      const created = await createRecording(file, consent, controller.signal)
      setJob(created)
      const finished = await pollRecording(created.job_id, controller.signal, setJob)
      if (finished.status === 'failed') setError(finished.error || '대화를 정리하지 못했어요. 다른 파일로 다시 시도해 주세요.')
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '업로드하지 못했어요.')
    } finally {
      if (controllerRef.current === controller) { controllerRef.current = null; setBusy(false) }
    }
  }
  function cancel() { resetResult(); setError('요청을 취소했어요. 서버에 올라간 원본은 처리 후 자동으로 지워져요.') }

  async function loadEvidence() {
    if (!timeline.length || evidenceBusy) return
    setEvidenceBusy(true); setError('')
    try { setEvidence(await findTimelineEvidence(timeline.map(e => ({ ...e, speaker: nameOf(e.speaker) })), language)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '근거를 찾지 못했어요.') }
    finally { setEvidenceBusy(false) }
  }

  const visible = timeline.map((entry, index) => ({ entry, index })).filter(({ entry }) => showOther || entry.category !== '기타')
  return <div className="recordings-page">
    <header className="recordings-heading"><div><p className="eyebrow">YOUR CONVERSATION</p><h1>대화 기록을 정리해 보세요</h1><p>녹음 파일을 올리면 말한 사람별로 글로 바꾸고, 임금·근무시간·약속 같은 중요한 발언을 정리해요.</p></div><Badge>{sample ? '고정 샘플' : '녹음 정리'}</Badge></header>
    <div className="recordings-notice"><strong>녹음 파일을 서버로 보내 CLOVA Speech로 글로 바꿔요</strong><p>원본 녹음은 처리가 끝나면 바로 지우고, 정리 결과도 1시간 뒤 사라져요. 녹음할 때는 상대방의 동의와 개인정보 보호를 고려해 주세요.</p></div>
    <div className="recordings-layout"><div className="recordings-column">
      <Card title="녹음 파일 선택" description="m4a, mp3, wav · 최대 200MB · 10분 이하"><label className="recordings-file" htmlFor="recording-file">녹음 파일 선택하기</label><input ref={inputRef} id="recording-file" type="file" accept=".m4a,.mp3,.wav,audio/mp4,audio/mpeg,audio/wav" disabled={busy} onChange={event => selectFile(event.target.files?.[0])} />{file && <div className="recordings-selected"><span>{file.name}</span><Button variant="ghost" disabled={busy} onClick={clearFile}>삭제</Button></div>}<label className="recordings-consent"><input type="checkbox" checked={consent} disabled={!file || busy} onChange={event => setConsent(event.target.checked)} />녹음 파일을 서버로 보내 처리하는 것과, 녹음에 개인정보가 포함될 수 있음을 확인했어요.</label><div className="recordings-actions"><Button disabled={!file || !consent} loading={busy} onClick={() => void start()}>대화 정리 시작</Button>{busy ? <Button variant="secondary" onClick={cancel}>취소</Button> : <Button variant="secondary" onClick={() => { resetResult(); setSample(true) }}>파일 없이 샘플 보기</Button>}</div><p className="recordings-error" role="alert">{error}</p>{job && job.status !== 'done' && job.status !== 'failed' && <p className="recordings-hint" role="status">{statusText[job.status]} · 몇 분 걸릴 수 있어요.</p>}</Card>
      {speakers.length > 0 && <Card title="화자 이름" description="화면에서만 이름을 바꿔요. 서버에 저장하지 않아요."><div className="speaker-fields">{speakers.map(id => <label key={id}>{defaultName(id)}<input value={names[id] ?? ''} placeholder={defaultName(id)} maxLength={30} onChange={event => setNames(previous => ({ ...previous, [id]: event.target.value }))} /></label>)}</div></Card>}
    </div><div className="recordings-column"><Card title="대화 타임라인" description="시각과 분류별 핵심 발언을 확인해 보세요." action={job?.duration_sec ? <Badge>{formatClock(job.duration_sec * 1000)}</Badge> : sample ? <Badge>고정 샘플</Badge> : undefined}>
      {busy && !timeline.length ? <StatePanel status="loading" title="대화를 정리하고 있어요" description={job ? statusText[job.status] : '파일을 올리고 있어요.'} />
        : !timeline.length ? <div className="recordings-empty"><p>아직 표시할 내용이 없어요.</p><p>{job?.status === 'done' ? '정리할 만한 발언을 찾지 못했어요. 전체 대본을 확인해 주세요.' : '녹음 파일을 올리거나 샘플을 열어 보세요.'}</p></div>
        : <><label className="recordings-filter"><input type="checkbox" checked={showOther} onChange={event => setShowOther(event.target.checked)} />기타 항목 보기</label><ol className="recordings-timeline">{visible.map(({ entry, index }) => { const ev = evidence?.entries.find(e => e.index === index); return <li key={`${entry.start_ms}-${index}`}><div><time>{formatClock(entry.start_ms)}</time><Badge>{entry.category}</Badge>{ev?.verbal_promise && <Badge tone="warning">말로 한 약속</Badge>}</div><strong>{nameOf(entry.speaker)}</strong><p>{entry.text}</p>{ev?.advice && <p className="recordings-advice">{ev.advice}</p>}{ev?.sources.map(source => { const href = safeOfficialUrl(source.url); return <div className="recordings-source" key={source.id}><span>{source.title}</span><SourceDetail id={source.id} />{href && <a href={href} target="_blank" rel="noreferrer">공식 원문 (새 탭)</a>}</div> })}</li> })}</ol>
          {!sample && <div className="recordings-actions"><Button variant="secondary" loading={evidenceBusy} onClick={() => void loadEvidence()}>{evidence ? '근거 다시 찾기' : '발언별 법령 근거 찾기'}</Button></div>}
          {evidence && <div className="recordings-evidence">{evidence.checklist_for_next_time.length > 0 && <><h3>다음에는 이렇게 확인해 보세요</h3><ul>{evidence.checklist_for_next_time.map(item => <li key={item}>{item}</li>)}</ul></>}<p className="recordings-hint">{evidence.disclaimer}</p></div>}
          <details className="recordings-transcript"><summary>전체 대본 보기</summary>{sample ? SAMPLE.map(e => <p key={e.start_ms}>{formatClock(e.start_ms)} · {nameOf(e.speaker)} : {e.text}</p>) : job?.segments?.length ? job.segments.map((s, i) => <p key={i}>{formatClock(s.start_ms)} · {nameOf(s.speaker)} : {s.text}</p>) : <p>{job?.transcript}</p>}</details></>}
    </Card></div></div>
  </div>
}
