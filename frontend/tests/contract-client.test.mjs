import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
test('OCR sends multipart and review sends confirmed JSON with cancellation', async () => {
  const { extractDocument, reviewContract } = await server.ssrLoadModule('/src/features/document-review/client.ts')
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return new Response(JSON.stringify({ success: true, data: { ok: true } })) }
  try {
    const signal = new AbortController().signal
    const file = new File(['synthetic'], 'sample.png', { type: 'image/png' })
    await extractDocument({ file, kind: 'image', docType: 'contract', language: 'ko' }, signal)
    assert.equal(calls[0].url, '/api/contracts/ocr')
    assert.equal(calls[0].init.body.get('file').name, file.name)
    assert.equal(calls[0].init.body.get('doc_type'), 'contract')
    assert.equal(calls[0].init.headers, undefined)
    const payload = { hourly_wage: 12000, weekly_hours: 20, year: 2026, work_days: ['월'], lang: 'ko' }
    await reviewContract(payload, signal)
    assert.equal(calls[1].url, '/api/contracts/review')
    assert.deepEqual(JSON.parse(calls[1].init.body), payload)
    assert.equal(calls[1].init.signal, signal)
  } finally { globalThis.fetch = original }
})
test('API errors and non-JSON responses are surfaced instead of sample fallback', async () => {
  const { request } = await server.ssrLoadModule('/src/api.ts')
  const original = globalThis.fetch
  try {
    globalThis.fetch = async () => new Response(JSON.stringify({ success: false, error: { code: 'OCR_FAILED', message: '인식 실패' } }), { status: 502 })
    await assert.rejects(request('/contracts/ocr'), error => error.code === 'OCR_FAILED')
    globalThis.fetch = async () => new Response('<html>error</html>', { status: 502 })
    await assert.rejects(request('/contracts/ocr'), /HTTP 502/)
  } finally { globalThis.fetch = original }
})
test('OCR session uses server values and always requires user confirmation', async () => {
  const { createOcrSession, canConfirmReview } = await server.ssrLoadModule('/src/features/document-review/model.ts')
  const f = value => ({ value, confidence: 'low', source_text: null })
  const ocr = { doc_type: 'contract', raw_text: 'synthetic', extracted: { hourly_wage: f(12345), weekly_hours: f(18), work_days: f(['월']), break_minutes: f(null) } }
  const s = createOcrSession({ file: new File(['x'], 'test.png'), kind: 'image', docType: 'contract', language: 'ko' }, ocr)
  assert.equal(s.draft.hourly_wage, '12345')
  assert.equal(s.draft.break_minutes, '')
  assert.equal(s.mode, 'manual')
  assert.equal(canConfirmReview(s), false)
})
