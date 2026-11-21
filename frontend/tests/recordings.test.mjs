import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())

test('recording selection accepts supported files and rejects empty, oversized or unsupported files', async () => {
  const { validateRecording } = await server.ssrLoadModule('/src/features/recordings/validation.ts')
  for (const name of ['test.MP3', 'test.wav', 'test.m4a']) assert.equal(validateRecording({ name, size: 200 * 1024 * 1024 }), null)
  assert.ok(validateRecording({ name: 'test.mp3', size: 0 }))
  assert.ok(validateRecording({ name: 'test.wav', size: 200 * 1024 * 1024 + 1 }))
  assert.ok(validateRecording({ name: 'test.pdf', size: 1 }))
})

test('initial screen requires file and consent before uploading, and keeps the sample entry', async () => {
  const { RecordingsPage } = await server.ssrLoadModule('/src/pages/RecordingsPage.tsx')
  const html = renderToStaticMarkup(createElement(RecordingsPage))
  assert.match(html, /CLOVA Speech/)
  assert.match(html, /disabled=""[^>]*>대화 정리 시작/)
  assert.match(html, /파일 없이 샘플 보기/)
})

test('recording client uploads with consent, polls until done and asks evidence for the timeline', async () => {
  const c = await server.ssrLoadModule('/src/features/recordings/client.ts')
  const original = globalThis.fetch
  const calls = []
  let polls = 0
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url, init })
    if (url === '/api/recordings') return new Response(JSON.stringify({ success: true, data: { job_id: 'j1', status: 'queued', speakers: [], segments: [], timeline: [] } }), { status: 202 })
    if (url === '/api/recordings/j1') { polls += 1; return new Response(JSON.stringify({ success: true, data: { job_id: 'j1', status: polls < 2 ? 'processing' : 'done', speakers: ['1'], segments: [], timeline: [{ start_ms: 61000, speaker: '1', text: '시급 만원', category: '임금' }] } })) }
    return new Response(JSON.stringify({ success: true, data: { entries: [], checklist_for_next_time: [], disclaimer: 'd' } }))
  }
  try {
    const file = new File(['x'], 'talk.m4a', { type: 'audio/mp4' })
    const job = await c.createRecording(file, true)
    assert.equal(calls[0].init.body.get('consent'), 'true')
    assert.equal(calls[0].init.body.get('file').name, 'talk.m4a')
    const seen = []
    const done = await c.pollRecording(job.job_id, new AbortController().signal, j => seen.push(j.status), 1)
    assert.deepEqual(seen, ['processing', 'done'])
    assert.equal(done.timeline[0].category, '임금')
    await c.findTimelineEvidence(done.timeline.concat(Array(60).fill(done.timeline[0])), 'en')
    const body = JSON.parse(calls.at(-1).init.body)
    assert.equal(calls.at(-1).url, '/api/recordings/evidence')
    assert.equal(body.entries.length, 50)
    assert.equal(body.lang, 'en')
    assert.equal(c.formatClock(61000), '01:01')
    assert.equal(c.formatClock(3_725_000), '1:02:05')
  } finally { globalThis.fetch = original }
})

test('polling stops when cancelled', async () => {
  const c = await server.ssrLoadModule('/src/features/recordings/client.ts')
  const original = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({ success: true, data: { job_id: 'j', status: 'processing', speakers: [], segments: [], timeline: [] } }))
  try {
    const controller = new AbortController()
    const pending = c.pollRecording('j', controller.signal, () => controller.abort(), 10_000)
    await assert.rejects(pending, { name: 'AbortError' })
  } finally { globalThis.fetch = original }
})
