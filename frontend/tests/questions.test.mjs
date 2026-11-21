import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
test('question length boundaries, trimmed JSON request, signal and server failures', async () => {
  const { askText, validateQuestion } = await server.ssrLoadModule('/src/features/questions/client.ts')
  assert.ok(validateQuestion('  ')); assert.ok(validateQuestion('가')); assert.ok(validateQuestion('가'.repeat(301)))
  assert.equal(validateQuestion('가'.repeat(300)), null)
  const original = globalThis.fetch
  const signal = new AbortController().signal
  const result = { question: '주휴수당?', route: 'faq', answer: '서버 답변', sources: [] }
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/api/ask/text'); assert.deepEqual(JSON.parse(init.body), { question: '주휴수당?' }); assert.equal(init.signal, signal)
      return new Response(JSON.stringify({ success: true, data: result }))
    }
    assert.deepEqual(await askText('  주휴수당?  ', signal), result)
    globalThis.fetch = async () => { throw new Error('must not send invalid question') }
    await assert.rejects(askText(' ', signal), /2~300/)
    globalThis.fetch = async () => new Response(JSON.stringify({ success: false, error: { code: 'AI_UNAVAILABLE', message: '서버 오류' } }), { status: 502 })
    await assert.rejects(askText('주휴수당?', signal), error => error.code === 'AI_UNAVAILABLE')
  } finally { globalThis.fetch = original }
})
test('question screen discloses transmission and removes fixed sample answer', async () => {
  const { QuestionPage } = await server.ssrLoadModule('/src/pages/QuestionPage.tsx')
  const html = renderToStaticMarkup(createElement(QuestionPage))
  assert.match(html, /질문을 서버로 보내 답변을 받아요/)
  assert.doesNotMatch(html, /고정된 예시|샘플 화면이에요/)
  assert.match(html, /2~300자/)
})
