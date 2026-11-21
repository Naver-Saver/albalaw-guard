import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
test('translation preserves calculation and original evidence, handles Korean locally and validates response', async () => {
  const { translateReview } = await server.ssrLoadModule('/src/features/check-results/translate.ts')
  const { getSampleResult } = await server.ssrLoadModule('/src/features/check-results/sampleResult.ts')
  const result = getSampleResult()
  const original = globalThis.fetch
  const signal = new AbortController().signal
  try {
    globalThis.fetch = async () => { throw new Error('Korean must not call server') }
    assert.deepEqual(await translateReview(result, 'ko', signal), result)
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/api/translate'); assert.equal(init.signal, signal)
      const body = JSON.parse(init.body)
      assert.ok(body.texts.length <= 30)
      return new Response(JSON.stringify({ success: true, data: { target: body.target, texts: body.texts.map(t => 'translated '+t) } }))
    }
    const translated = await translateReview(result, 'en', signal)
    assert.deepEqual(translated.calculation, result.calculation)
    assert.deepEqual(translated.sources, result.sources)
    assert.match(translated.items[0].title, /^translated /)
    assert.notEqual(translated.disclaimer, result.disclaimer)
    assert.doesNotMatch(result.items[0].title, /^translated /)
    globalThis.fetch = async () => new Response(JSON.stringify({ success: true, data: { target: 'en', texts: [] } }))
    await assert.rejects(translateReview(result, 'en', signal), /번역 응답/)
  } finally { globalThis.fetch = original }
})
