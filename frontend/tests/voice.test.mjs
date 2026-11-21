import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
test('WAV encoder emits mono PCM16 with duration metadata and clips sample values', async () => {
  const { encodeWav } = await server.ssrLoadModule('/src/features/questions/audio.ts')
  const blob = encodeWav(new Float32Array([-2, 0, 2]), 16000)
  const data = new DataView(await blob.arrayBuffer())
  assert.equal(blob.type, 'audio/wav'); assert.equal(blob.size, 50)
  assert.equal(data.getUint32(24, true), 16000); assert.equal(data.getUint16(22, true), 1)
  assert.equal(data.getInt16(44, true), -32768); assert.equal(data.getInt16(48, true), 32767)
  assert.throws(() => encodeWav(new Float32Array(16000 * 60 + 1), 16000), /60초/)
  assert.throws(() => encodeWav(new Float32Array(), 16000), /60초/)
})
test('voice request uses multipart with cancellation and returns recognized question', async () => {
  const { askVoice } = await server.ssrLoadModule('/src/features/questions/client.ts')
  const original = globalThis.fetch
  const signal = new AbortController().signal
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/api/ask/voice'); assert.equal(init.signal, signal)
      assert.equal(init.headers, undefined); assert.equal(init.body.get('file').name, 'voice.wav')
      return new Response(JSON.stringify({ success: true, data: { question: '인식된 질문', route: 'faq', answer: '답변', sources: [] } }))
    }
    assert.equal((await askVoice(new File(['wav'], 'voice.wav'), signal)).question, '인식된 질문')
    await assert.rejects(askVoice(new File([], 'voice.wav'), signal))
    await assert.rejects(askVoice(new File(['x'], 'voice.webm'), signal))
  } finally { globalThis.fetch = original }
})
test('microphone initialization failure releases captured tracks', async () => {
  const { startMicrophone } = await server.ssrLoadModule('/src/features/questions/audio.ts')
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  const oldContext = globalThis.AudioContext
  let stopped = false
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() { stopped = true } }] }) } } })
  globalThis.AudioContext = class { constructor() { throw new Error('unavailable') } }
  try { await assert.rejects(startMicrophone(() => {})); assert.equal(stopped, true) }
  finally { if (descriptor) Object.defineProperty(globalThis, 'navigator', descriptor); else delete globalThis.navigator; globalThis.AudioContext = oldContext }
})
