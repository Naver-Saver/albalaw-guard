import { request } from '../../api'
import type { Source } from '../check-results/types'
import type { Language } from '../document-upload/validation'

export type TimelineCategory = '임금' | '근무시간' | '휴게·휴일' | '약속·지시' | '기타'
export type TimelineEntry = { start_ms: number; speaker: string; text: string; category: TimelineCategory }
export type RecordingJob = {
  job_id: string; status: 'queued' | 'processing' | 'done' | 'failed'; error?: string | null; duration_sec?: number | null
  speakers: string[]; segments: { start_ms: number; end_ms: number; speaker: string; text: string }[]; timeline: TimelineEntry[]; transcript?: string | null
}
export type EntryEvidence = { index: number; start_ms: number; sources: Source[]; verbal_promise: boolean; advice?: string | null }
export type TimelineEvidence = { entries: EntryEvidence[]; checklist_for_next_time: string[]; disclaimer: string }

/** API-05: 녹음 업로드 → 작업 생성 (원본은 처리 후 서버가 바로 지운다) */
export function createRecording(file: File, consent: boolean, signal?: AbortSignal) {
  const body = new FormData()
  body.append('file', file)
  body.append('consent', String(consent))
  return request<RecordingJob>('/recordings', { method: 'POST', body, signal })
}
/** API-06: 작업 상태·타임라인 조회 */
export function getRecording(jobId: string, signal?: AbortSignal) {
  return request<RecordingJob>(`/recordings/${encodeURIComponent(jobId)}`, { signal })
}
/** API-15: 타임라인 발언의 근거와 '말로만 한 약속' 안내 (최대 50개, 발언 500자) */
export function findTimelineEvidence(entries: TimelineEntry[], lang: Language, signal?: AbortSignal) {
  const body = { entries: entries.slice(0, 50).map(e => ({ ...e, speaker: e.speaker.slice(0, 30), text: e.text.slice(0, 500) })), lang }
  return request<TimelineEvidence>('/recordings/evidence', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })
}

export function formatClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), s = total % 60
  const mmss = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return h ? `${h}:${mmss}` : mmss
}

/** 끝난 작업이 나올 때까지 interval 간격으로 조회한다. 취소 신호가 오면 멈춘다. */
export async function pollRecording(jobId: string, signal: AbortSignal, onUpdate: (job: RecordingJob) => void, interval = 3000): Promise<RecordingJob> {
  const cancelled = () => new DOMException('Cancelled', 'AbortError')
  for (;;) {
    if (signal.aborted) throw cancelled()
    const job = await getRecording(jobId, signal)
    if (signal.aborted) throw cancelled()
    onUpdate(job)
    if (job.status === 'done' || job.status === 'failed') return job
    await new Promise<void>((resolve, reject) => {
      if (signal.aborted) { reject(cancelled()); return }
      const timer = setTimeout(resolve, interval)
      signal.addEventListener('abort', () => { clearTimeout(timer); reject(cancelled()) }, { once: true })
    })
  }
}
