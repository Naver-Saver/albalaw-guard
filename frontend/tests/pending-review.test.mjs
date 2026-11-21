import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
test('an extracted document awaiting confirmation directs the user to edit, not file replacement', async () => {
  const { PendingReviewResult } = await server.ssrLoadModule('/src/pages/PendingReviewResult.tsx')
  const html = renderToStaticMarkup(createElement(PendingReviewResult, { onReview() {} }))
  assert.match(html, /문서는 이미 준비돼 있어요/)
  assert.match(html, /추출 내용 확인으로 돌아가기/)
  assert.doesNotMatch(html, />문서 선택하기</)
  assert.doesNotMatch(html, /파일 없이 샘플/)
})
