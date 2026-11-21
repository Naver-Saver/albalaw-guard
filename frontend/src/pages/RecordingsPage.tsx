import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Status'
import { Card } from '../components/common/Card'
import { validateRecording } from '../features/recordings/validation'
import { createRecording, pollRecording, formatRecordingTime } from '../features/recordings/client'
import type { RecordingJob } from '../features/recordings/client'
import './recordings.css'

const sample: RecordingJob = { job_id: 'sample', status: 'done', speakers: ['화자 A', '화자 B'], timeline: [
  { start_ms: 12000, speaker: '화자 A', category: '임금', text: '이번 달부터 시급을 조정할게요.' },
  { start_ms: 65000, speaker: '화자 B', category: '근무시간', text: '다음 주 근무시간을 확인하고 싶어요.' },
  { start_ms: 90000, speaker: '화자 A', category: '기타', text: '확인한 뒤 다시 알려드릴게요.' },
], transcript: '화자 A: 이번 달부터 시급을 조정할게요.\n화자 B: 다음 주 근무시간을 확인하고 싶어요.\n화자 A: 확인한 뒤 다시 알려드릴게요.' }

export function RecordingsPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const requestRef = useRef<AbortController | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [consent, setConsent] = useState(false)
  const [showSample, setShowSample] = useState(false)
  const [showOther, setShowOther] = useState(false)
  const [names, setNames] = useState<Record<string, string>>({})
  const [job, setJob] = useState<RecordingJob | null>(null)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const stop = useCallback(() => requestRef.current?.abort(), [])
  useEffect(() => stop, [stop])

  function selectFile(next?: File) {
    if (requestRef.current) return
    setShowSample(false); setConsent(false); setJob(null); setNames({}); setStatus('')
    const problem = next ? validateRecording(next) : null
    setFile(problem ? null : next ?? null); setError(problem ?? '')
  }
  function clearFile() { selectFile(); if (inputRef.current) inputRef.current.value = '' }
  async function process(resume = false) {
    if (requestRef.current || (!resume && (!file || !consent))) return
    const controller = new AbortController(); requestRef.current = controller
    setBusy(true); setError(''); setShowSample(false)
    setStatus(resume ? '기존 작업 상태를 확인하고 있어요.' : '녹음 파일을 전송하고 있어요.')
    try {
      const initial = resume && job ? job : await createRecording(file!, consent, controller.signal)
      if (controller.signal.aborted) return
      setJob(initial)
      if (initial.status === 'failed') throw new Error(initial.error || '녹음 처리에 실패했어요.')
      const complete = initial.status === 'done' ? initial : await pollRecording(initial.job_id, controller.signal, current => {
        setJob(current); setStatus(current.status === 'queued' ? '녹음 처리를 기다리고 있어요.' : '음성을 인식하고 타임라인을 정리하고 있어요.')
      })
      if (!controller.signal.aborted) { setJob(complete); setStatus('대화 정리를 완료했어요.') }
    } catch (reason) {
      if (!controller.signal.aborted) { setError(reason instanceof Error ? reason.message : '녹음 처리에 실패했어요.'); setStatus('') }
    } finally {
      if (requestRef.current === controller) { requestRef.current = null; setBusy(false); if (controller.signal.aborted) setStatus('조회가 중지됐어요. 서버 작업은 계속될 수 있어요. 같은 작업을 다시 조회할 수 있어요.') }
    }
  }
  const displayed = showSample ? sample : job?.status === 'done' ? job : null
  const speakers = displayed ? [...new Set([...displayed.speakers, ...displayed.timeline.map(entry => entry.speaker)])] : []
  function download() {
    if (!displayed?.transcript) return
    const url = URL.createObjectURL(new Blob([displayed.transcript], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = showSample ? 'sample-transcript.txt' : 'recording-transcript.txt'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <div className="recordings-page">
    <header className="recordings-heading"><div><p className="eyebrow">YOUR CONVERSATION</p><h1>대화 기록을 정리해 보세요</h1><p>녹음 파일을 보내 실제 타임라인과 대본을 확인할 수 있어요.</p></div><Badge>{showSample ? '고정 샘플' : '녹음 정리'}</Badge></header>
    <div className="recordings-notice"><strong>동의 후 파일을 서버로 전송해요</strong><p>음성을 인식하고 대화를 정리하기 위해 임시 저장해 처리해요. 상대방의 동의와 개인정보 보호를 고려해 주세요. 파일 없는 샘플 체험은 전송하거나 분석하지 않아요. 샘플 결과는 선택한 파일과 관계없는 고정 샘플이에요.</p></div>
    <div className="recordings-layout"><div className="recordings-column">
      <Card title="녹음 파일 선택" description="m4a, mp3, wav · 최대 200MB · 최대 10분"><label className="recordings-file" htmlFor="recording-file">녹음 파일 선택하기</label><input ref={inputRef} id="recording-file" type="file" disabled={busy} accept=".m4a,.mp3,.wav,audio/mp4,audio/mpeg,audio/wav" onChange={event => selectFile(event.target.files?.[0])} />{file && <div className="recordings-selected"><span>{file.name}</span><Button variant="ghost" disabled={busy} onClick={clearFile}>삭제</Button></div>}<p className="recordings-hint">서버에서 길이를 확인해요. 새 파일 업로드는 새 분석 요청이며 비용이 발생할 수 있어요.</p><label className="recordings-consent"><input type="checkbox" checked={consent} disabled={busy} onChange={event => setConsent(event.target.checked)} />녹음 내용의 개인정보·상대방 권리를 확인했고 서버 처리에 동의해요.</label><div className="recordings-actions"><Button disabled={!file || !consent || busy || !!job} onClick={() => void process()}>녹음 정리 요청</Button><Button disabled={busy} variant="secondary" onClick={() => { setShowSample(true); setNames({}) }}>파일 없이 샘플 보기</Button></div>{busy && <Button variant="secondary" onClick={stop}>조회 중지</Button>}{job && job.status !== 'done' && job.status !== 'failed' && !busy && <Button variant="secondary" onClick={() => void process(true)}>같은 작업 다시 조회</Button>}{job?.status === 'failed' && <p>서버에서 작업이 실패했어요. 파일을 다시 선택해 새로 요청할 수 있어요.</p>}<p role="status">{status}</p>{error && <p className="recordings-error" role="alert">{error}</p>}<p className="recordings-hint">화면을 나가면 조회를 중지해요. 서버 작업 취소를 뜻하지 않아요. 이 화면의 작업 정보는 새로고침하거나 나가면 초기화돼요.</p></Card>
      <Card title="화자 이름" description="화면에서만 이름을 바꿀 수 있어요."><div className="speaker-fields">{speakers.length ? speakers.map(speaker => <label key={speaker}>{speaker}<input value={names[speaker] ?? speaker} maxLength={30} onChange={event => setNames(previous => ({ ...previous, [speaker]: event.target.value }))} /></label>) : <p>대화 정리가 완료되면 화자를 표시해요.</p>}</div></Card>
    </div><div className="recordings-column"><Card title="대화 타임라인" description="시각과 분류별 핵심 발언을 확인해 보세요." action={displayed ? <Badge>{showSample ? '고정 샘플' : '서버 응답'}</Badge> : undefined}>
      {!displayed ? <div className="recordings-empty"><p>{busy ? '녹음 처리 중이에요.' : '아직 표시할 내용이 없어요.'}</p><p>실제 녹음 정리를 요청하거나 파일 없이 샘플을 살펴보세요.</p></div> : <><label className="recordings-filter"><input type="checkbox" checked={showOther} onChange={event => setShowOther(event.target.checked)} />기타 항목 보기</label><ol className="recordings-timeline">{displayed.timeline.filter(entry => showOther || entry.category !== '기타').map((entry, index) => <li key={`${entry.start_ms}-${index}`}><div><time>{formatRecordingTime(entry.start_ms)}</time><Badge>{entry.category}</Badge></div><strong>{names[entry.speaker]?.trim() || entry.speaker}</strong><p>{entry.text}</p></li>)}</ol>{!displayed.timeline.filter(entry => showOther || entry.category !== '기타').length && <p>현재 분류에서 표시할 핵심 발언이 없어요. 대본도 확인해 주세요.</p>}<details className="recordings-transcript"><summary>{showSample ? '샘플 전체 대본 보기' : '전체 대본 보기'}</summary><p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{displayed.transcript || '대본이 제공되지 않았어요.'}</p></details><Button variant="secondary" disabled={!displayed.transcript} onClick={download}>대본 내려받기</Button></>}
    </Card></div></div>
  </div>
}
