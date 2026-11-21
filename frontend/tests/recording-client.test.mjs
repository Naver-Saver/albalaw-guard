import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
const json = data => new Response(JSON.stringify({ success: true, data }))
test('upload validates consent, sends multipart and polls the same job until done without reupload', async () => {
  const { createRecording, pollRecording } = await server.ssrLoadModule('/src/features/recordings/client.ts')
  const original = globalThis.fetch
  const file = new File(['synthetic'], 'test.mp3')
  const signal = new AbortController().signal
  const calls = []; const states = ['queued', 'processing', 'done']
  try {
    globalThis.fetch = async (url, init) => {
      calls.push(url); assert.equal(init.signal, signal)
      if (init.method === 'POST') { assert.equal(init.body.get('consent'), 'true'); assert.equal(init.body.get('file').name, 'test.mp3'); assert.equal(init.headers, undefined); return json({ job_id: 'rec_test', status: 'queued' }) }
      return json({ job_id: 'rec_test', status: states.shift(), speakers: [], timeline: [], transcript: '대본' })
    }
    await assert.rejects(createRecording(file, false, signal))
    assert.equal(calls.length, 0)
    const job = await createRecording(file, true, signal)
    const observed = []
    const done = await pollRecording(job.job_id, signal, value => observed.push(value.status), async () => {})
    assert.equal(done.transcript, '대본'); assert.deepEqual(observed, ['queued', 'processing', 'done'])
    assert.deepEqual(calls, ['/api/recordings', '/api/recordings/rec_test', '/api/recordings/rec_test', '/api/recordings/rec_test'])
  } finally { globalThis.fetch = original }
})
test('failed, timed-out and cancelled polling never returns sample results', async () => {
  const { pollRecording, pollingDelay, formatRecordingTime } = await server.ssrLoadModule('/src/features/recordings/client.ts')
  const original = globalThis.fetch
  const signal = new AbortController().signal
  try {
    globalThis.fetch = async () => json({ job_id: 'rec_x', status: 'failed', error: '인식 실패' })
    await assert.rejects(pollRecording('rec_x', signal, () => {}, async () => {}), /인식 실패/)
    let calls = 0
    globalThis.fetch = async () => { calls++; return json({ job_id: 'rec_x', status: 'processing' }) }
    await assert.rejects(pollRecording('rec_x', signal, () => {}, async () => {}), /5분/)
    assert.equal(calls, 100)
    const controller = new AbortController()
    const delay = pollingDelay(controller.signal); controller.abort()
    await assert.rejects(delay, { name: 'AbortError' })
    await assert.rejects(pollRecording('rec_x', controller.signal, () => {}, async () => {}), { name: 'AbortError' })
    assert.equal(calls, 100)
    assert.equal(formatRecordingTime(65000), '01:05')
  } finally { globalThis.fetch = original }
})
