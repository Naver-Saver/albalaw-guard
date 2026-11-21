import { request } from '../../api'
import { validateRecording } from './validation'

export type TimelineEntry = { start_ms: number; speaker: string; text: string; category: '임금' | '근무시간' | '휴게·휴일' | '약속·지시' | '기타' }
export type RecordingJob = { job_id: string; status: 'queued' | 'processing' | 'done' | 'failed'; error?: string | null; speakers: string[]; timeline: TimelineEntry[]; transcript?: string | null; duration_sec?: number | null }
export function createRecording(file: File, consent: boolean, signal: AbortSignal) {
  const error = validateRecording(file)
  if (error || !consent) return Promise.reject(new Error(error || '녹음 처리 안내에 동의해 주세요.'))
  const body = new FormData(); body.append('file', file); body.append('consent', 'true')
  return request<RecordingJob>('/recordings', { method: 'POST', body, signal })
}
export function getRecording(id: string, signal: AbortSignal) {
  return request<RecordingJob>(`/recordings/${encodeURIComponent(id)}`, { signal })
}
export function pollingDelay(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(new DOMException('조회 중지', 'AbortError')); return }
    const abort = () => { clearTimeout(timer); reject(new DOMException('조회 중지', 'AbortError')) }
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve() }, 3000)
    signal.addEventListener('abort', abort, { once: true })
  })
}
export async function pollRecording(id: string, signal: AbortSignal, onStatus: (job: RecordingJob) => void, delay = pollingDelay): Promise<RecordingJob> {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (signal.aborted) throw new DOMException('조회 중지', 'AbortError')
    const job = await getRecording(id, signal)
    if (signal.aborted) throw new DOMException('조회 중지', 'AbortError')
    onStatus(job)
    if (job.status === 'failed') throw new Error(job.error || '녹음 처리에 실패했어요.')
    if (job.status === 'done') return job
    await delay(signal)
  }
  throw new Error('5분 동안 처리가 끝나지 않았어요. 잠시 후 같은 작업을 다시 조회해 주세요.')
}
export function formatRecordingTime(ms: number) {
  const seconds = Math.floor(Math.max(0, ms) / 1000)
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}
