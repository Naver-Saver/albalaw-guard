import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
const load = () => server.ssrLoadModule('/src/features/document-upload/validation.ts')
const file = (name = 'contract.jpg', size = 1024, type = 'image/jpeg') => ({ name, size, type })

test('accepts JPG, JPEG, PNG and PDF including uppercase extensions and absent MIME', async () => {
  const { validateDocumentFiles, MAX_DOCUMENT_BYTES } = await load()
  for (const f of [file(), file('contract.JPEG'), file('pay.png', 1024, 'image/png'), file('pay.pdf', 1024, 'application/pdf'), file('mobile.jpg', 1024, ''), file('limit.jpg', MAX_DOCUMENT_BYTES)]) {
    assert.equal(validateDocumentFiles([f]).error, null, f.name)
  }
  assert.equal(validateDocumentFiles([file('pay.pdf', 1024, 'application/pdf')]).kind, 'pdf')
})

test('rejects missing, multiple, empty and over-limit files', async () => {
  const { validateDocumentFiles, MAX_DOCUMENT_BYTES } = await load()
  assert.match(validateDocumentFiles([]).error, /선택/)
  assert.match(validateDocumentFiles([file(), file()]).error, /1개/)
  assert.match(validateDocumentFiles([file('empty.jpg', 0)]).error, /빈 파일/)
  assert.match(validateDocumentFiles([file('large.jpg', MAX_DOCUMENT_BYTES + 1)]).error, /10MB/)
})

test('rejects unsupported and misleading file types', async () => {
  const { validateDocumentFiles } = await load()
  for (const f of [file('photo.gif', 1024, 'image/gif'), file('file', 1024, ''), file('image.jpg.exe'), file('image.jpg', 1024, 'application/pdf')]) {
    assert.ok(validateDocumentFiles([f]).error, f.name)
  }
})

test('leaving a preview request cancels the pending simulation', async () => {
  const { simulateExtraction } = await server.ssrLoadModule('/src/features/document-upload/simulateExtraction.ts')
  const controller = new AbortController()
  const pending = simulateExtraction(controller.signal)
  controller.abort()
  await assert.rejects(pending, { name: 'AbortError' })
  await assert.rejects(simulateExtraction(controller.signal), { name: 'AbortError' })
})

test('a MIME-less PDF preview is explicitly typed as PDF rather than sniffed as HTML', async () => {
  const { createPreviewBlob } = await server.ssrLoadModule('/src/features/document-upload/previewBlob.ts')
  const original = new File(['<html>mislabeled</html>'], 'document.pdf', { type: '' })
  const preview = createPreviewBlob(original, 'pdf')
  assert.equal(preview.type, 'application/pdf')
  assert.equal(original.type, '')
  const jpeg = new File(['image bytes'], 'camera.JPG', { type: '' })
  assert.equal(createPreviewBlob(jpeg, 'image').type, 'image/jpeg')
})

test('initial upload screen states local-only mode and disables extraction', async () => {
  const { DocumentUploadPage } = await server.ssrLoadModule('/src/pages/DocumentUploadPage.tsx')
  const html = renderToStaticMarkup(createElement(DocumentUploadPage))
  assert.match(html, /서버로 전송되지 않아요/)
  assert.match(html, /type="file"/)
  assert.match(html, /capture="environment"/)
  assert.match(html, /type="checkbox"/)
  assert.match(html, /<button[^>]*disabled[^>]*>문서 내용 추출하기 \(체험\)/)
  assert.match(html, /10MB/)
})
