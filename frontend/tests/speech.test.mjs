import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'

const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())

test('TTS returns audio, trims to 1000 chars, and surfaces server errors', async () => {
  const { synthesizeSpeech, TTS_MAX_CHARS } = await server.ssrLoadModule('/src/features/speech/client.ts')
  const original = globalThis.fetch
  try {
    let sent
    globalThis.fetch = async (url, init) => { sent = { url, body: JSON.parse(init.body) }; return new Response(new Uint8Array([1, 2, 3]), { headers: { 'content-type': 'audio/mpeg' } }) }
    const blob = await synthesizeSpeech('  가'.repeat(600), 'en')
    assert.equal(sent.url, '/api/tts')
    assert.equal(sent.body.lang, 'en')
    assert.equal(sent.body.text.length, TTS_MAX_CHARS)
    assert.equal(blob.size, 3)
    globalThis.fetch = async () => new Response(JSON.stringify({ success: false, error: { code: 'AI_UNAVAILABLE', message: '음성 합성 실패' } }), { status: 502 })
    await assert.rejects(synthesizeSpeech('안녕', 'ko'), { code: 'AI_UNAVAILABLE', message: '음성 합성 실패' })
  } finally { globalThis.fetch = original }
})

test('answer translation skips Korean and calls /translate otherwise', async () => {
  const { translateText } = await server.ssrLoadModule('/src/features/speech/client.ts')
  const original = globalThis.fetch
  const calls = []
  try {
    globalThis.fetch = async (url, init) => { calls.push({ url, body: JSON.parse(init.body) }); return new Response(JSON.stringify({ success: true, data: { texts: ['Hello'], target: 'en' } })) }
    assert.equal(await translateText('안녕', 'ko'), '안녕')
    assert.equal(calls.length, 0)
    assert.equal(await translateText('안녕', 'en'), 'Hello')
    assert.deepEqual(calls[0], { url: '/api/translate', body: { texts: ['안녕'], target: 'en' } })
  } finally { globalThis.fetch = original }
})
