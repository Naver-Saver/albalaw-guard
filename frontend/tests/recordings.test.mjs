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

test('initial screen explains sample status and requires file and consent for the file flow', async () => {
  const { RecordingsPage } = await server.ssrLoadModule('/src/pages/RecordingsPage.tsx')
  const html = renderToStaticMarkup(createElement(RecordingsPage))
  assert.match(html, /전송하거나 분석하지 않아요/)
  assert.match(html, /선택한 파일과 관계없는 고정 샘플/)
  assert.match(html, /disabled=""[^>]*>샘플 결과 보기/)
  assert.match(html, /파일 없이 샘플 보기/)
})
