import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from './common/Button'
import { askVoice } from '../features/questions/client'
import type { AskResult } from '../features/questions/client'
import { prepareVoiceFile, startMicrophone } from '../features/questions/audio'
import { useObjectUrl } from '../features/document-upload/useObjectUrl'

export function VoiceQuestion({ disabled, onBusy, onResult }: { disabled: boolean; onBusy: (busy: boolean) => void; onResult: (result: AskResult) => void }) {
  const [state, setState] = useState<'idle' | 'preparing' | 'recording' | 'sending'>('idle')
  const [file, setFile] = useState<File | null>(null)
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState('')
  const alive = useRef(true)
  const operation = useRef(0)
  const recorder = useRef<Awaited<ReturnType<typeof startMicrophone>> | null>(null)
  const request = useRef<AbortController | null>(null)
  const { url, setPreviewFile } = useObjectUrl()
  const cleanup = useCallback(() => { alive.current = false; operation.current++; recorder.current?.cancel(); request.current?.abort() }, [])
  useEffect(() => { alive.current = true; return cleanup }, [cleanup])
  function ready(audio: File | null) {
    if (!alive.current) return
    recorder.current = null; setFile(audio); setPreviewFile(audio); setConsent(false); setState('idle'); onBusy(false)
  }
  async function record() {
    if (state !== 'idle' || disabled) return
    const id = ++operation.current; setError(''); setFile(null); setPreviewFile(null); setState('preparing'); onBusy(true)
    try {
      const handle = await startMicrophone(ready)
      if (!alive.current || operation.current !== id) { handle.cancel(); return }
      recorder.current = handle; setState('recording')
    } catch { if (alive.current && operation.current === id) { setError('마이크를 사용할 수 없어요. 권한을 확인하거나 음성 파일을 선택해 주세요.'); setState('idle'); onBusy(false) } }
  }
  async function choose(next?: File) {
    if (!next || state !== 'idle' || disabled) return
    const id = ++operation.current; setState('preparing'); onBusy(true); setError(''); setFile(null); setPreviewFile(null)
    try { const audio = await prepareVoiceFile(next); if (alive.current && operation.current === id) ready(audio) }
    catch (reason) { if (alive.current && operation.current === id) { setError(reason instanceof Error ? reason.message : '음성을 읽지 못했어요.'); setState('idle'); onBusy(false) } }
  }
  async function send() {
    if (!file || !consent || disabled || state !== 'idle' || request.current) return
    const controller = new AbortController(); request.current = controller; setState('sending'); onBusy(true); setError('')
    try { const result = await askVoice(file, controller.signal); if (!controller.signal.aborted && alive.current) { onResult(result); setFile(null); setPreviewFile(null); setConsent(false) } }
    catch (reason) { if (!controller.signal.aborted && alive.current) setError(reason instanceof Error ? reason.message : '음성 질문에 실패했어요.') }
    finally { if (request.current === controller) { request.current = null; if (alive.current) { setState('idle'); onBusy(false) } } }
  }
  const busy = state !== 'idle'
  const microphone = typeof window !== 'undefined' && window.isSecureContext && !!navigator.mediaDevices?.getUserMedia
  return <section className="question-form" aria-label="음성 질문"><h2>음성으로 질문하기</h2><p>한국어 음성 · 최대 60초 · WAV/MP3 파일은 최대 10MB. 녹음 종료 후 미리 듣고 동의하면 서버로 전송해요.</p>{!microphone && <p>현재 접속에서는 마이크를 사용할 수 없어요. HTTPS 또는 localhost에서 녹음하거나, 음성 파일을 선택해 주세요.</p>}<div><Button disabled={!microphone || disabled || busy} onClick={() => void record()}>녹음 시작</Button>{state === 'recording' && <Button variant="secondary" onClick={() => recorder.current?.stop()}>녹음 종료</Button>}</div><label>음성 파일 선택<input type="file" accept=".wav,.mp3,audio/wav,audio/mpeg" disabled={disabled || busy} onChange={event => { void choose(event.target.files?.[0]); event.target.value = '' }} /></label><p role="status">{state === 'recording' ? '녹음 중 · 60초가 되면 자동 종료돼요.' : state === 'preparing' ? '음성을 준비하고 있어요.' : state === 'sending' ? '음성을 인식하고 답변을 확인하고 있어요.' : file ? '음성이 준비됐어요.' : ''}</p>{url && <audio controls src={url} preload="metadata" />}<label><input type="checkbox" checked={consent} disabled={!file || busy} onChange={event => setConsent(event.target.checked)} />음성에 개인정보가 없는지 확인했고 서버 전송에 동의해요.</label><Button disabled={!file || !consent || disabled || busy} onClick={() => void send()}>음성 질문 보내기</Button>{state === 'sending' && <Button variant="secondary" onClick={() => request.current?.abort()}>요청 취소</Button>}{error && <p role="alert">{error}</p>}</section>
}
