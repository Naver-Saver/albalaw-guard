import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
const load = () => server.ssrLoadModule('/src/features/document-review/model.ts')

test('sample OCR maps values and uncertainty, while real uploads start without invented values', async () => {
  const { createReviewSession } = await load()
  const sample = createReviewSession('sample', undefined, 2026)
  assert.equal(sample.draft.hourly_wage, '10000')
  assert.equal(sample.draft.weekly_hours, '20')
  assert.equal(sample.draft.break_minutes, '')
  assert.equal(sample.ocr.extracted.weekly_hours.confidence, 'low')
  const manual = createReviewSession('manual', { file: new File(['image'], 'contract.jpg'), kind: 'image', docType: 'contract', language: 'ko' }, 2026)
  assert.equal(manual.ocr, null)
  assert.equal(manual.draft.hourly_wage, '')
  assert.equal(manual.draft.weekly_hours, '')
})

test('validation blocks missing, negative, non-finite and out-of-range inputs without rejecting zero', async () => {
  const { createReviewSession, validateReviewDraft } = await load()
  const draft = createReviewSession('sample', undefined, 2026).draft
  assert.deepEqual(validateReviewDraft(draft), {})
  for (const hourly_wage of ['', '-1', 'NaN', 'Infinity', '1e4', '10,00', '1.5']) assert.ok(validateReviewDraft({ ...draft, hourly_wage }).hourly_wage, hourly_wage)
  for (const weekly_hours of ['', '-1', '169', 'Infinity']) assert.ok(validateReviewDraft({ ...draft, weekly_hours }).weekly_hours, weekly_hours)
  for (const break_minutes of ['-1', '1441', '1.5']) assert.ok(validateReviewDraft({ ...draft, break_minutes }).break_minutes, break_minutes)
  assert.ok(validateReviewDraft({ ...draft, year: '' }).year)
  assert.ok(validateReviewDraft({ ...draft, year: '2026.5' }).year)
  assert.ok(validateReviewDraft({ ...draft, work_days: ['월', '월'] }).work_days)
  assert.ok(validateReviewDraft({ ...draft, work_days: ['X'] }).work_days)
  assert.deepEqual(validateReviewDraft({ ...draft, hourly_wage: '0', weekly_hours: '0', break_minutes: '0' }), {})
})

test('confirmation is mandatory and every edit revokes it', async () => {
  const { createReviewSession, canConfirmReview, editReviewSession } = await load()
  const initial = createReviewSession('sample', undefined, 2026)
  assert.equal(canConfirmReview(initial), false)
  const confirmed = { ...initial, confirmed: true }
  assert.equal(canConfirmReview(confirmed), true)
  const changed = editReviewSession(confirmed, { ...confirmed.draft, weekly_hours: '25.5' })
  assert.equal(changed.confirmed, false)
  assert.equal(canConfirmReview(changed), false)
  assert.equal(canConfirmReview({ ...confirmed, draft: { ...confirmed.draft, hourly_wage: '' } }), false)
})

test('request serialization matches API-04 and preserves empty optional values and source data', async () => {
  const { createReviewSession, toReviewRequest } = await load()
  const session = createReviewSession('sample', undefined, 2026)
  const payload = toReviewRequest({ ...session, confirmed: true, draft: { ...session.draft, hourly_wage: '12,000', weekly_hours: '25.5', work_days: ['월', '수'], break_minutes: '30' } })
  assert.deepEqual(payload, { hourly_wage: 12000, weekly_hours: 25.5, work_days: ['월', '수'], break_minutes: 30, year: 2026, lang: 'ko' })
  assert.equal(session.ocr.extracted.hourly_wage.value, 10000)
  assert.equal('break_minutes' in toReviewRequest({ ...session, confirmed: true }), false)
  assert.equal(toReviewRequest({ ...session, confirmed: true, draft: { ...session.draft, break_minutes: '0' } }).break_minutes, 0)
  assert.equal(toReviewRequest({ ...session, confirmed: true, language: 'vi' }).lang, 'vi')
  assert.throws(() => toReviewRequest(session))
})

test('sample review labels sample data, identifies uncertain values and disables unconfirmed submission', async () => {
  const { createReviewSession } = await load()
  const { DocumentReviewPage } = await server.ssrLoadModule('/src/pages/DocumentReviewPage.tsx')
  const html = renderToStaticMarkup(createElement(DocumentReviewPage, { session: createReviewSession('sample', undefined, 2026), onChange: () => {}, onReplace: () => {}, onConfirm: () => {} }))
  assert.match(html, /샘플 OCR/)
  assert.match(html, /확인 필요/)
  assert.match(html, /시급/)
  assert.match(html, /disabled[^>]*>수정 내용으로 점검 \(체험\)/)
  assert.equal((html.match(/>다른 문서로 교체<\/button>/g) ?? []).length, 1)
  assert.equal((html.match(/>확대해서 보기<\/button>/g) ?? []).length, 1)
})

test('manual review keeps the uploaded file and never presents sample numbers as OCR output', async () => {
  const { createReviewSession } = await load()
  const { DocumentReviewPage } = await server.ssrLoadModule('/src/pages/DocumentReviewPage.tsx')
  const file = new File(['pdf'], 'pay.pdf', { type: 'application/pdf' })
  const session = createReviewSession('manual', { file, kind: 'pdf', docType: 'payslip', language: 'vi' }, 2026)
  assert.equal(session.document.file, file)
  assert.equal(session.language, 'vi')
  const html = renderToStaticMarkup(createElement(DocumentReviewPage, { session, onChange: () => {}, onReplace: () => {}, onConfirm: () => {} }))
  assert.match(html, /직접 입력/)
  assert.match(html, /원본을 보고 직접 입력해 주세요/)
  assert.match(html, /급여명세서/)
  assert.doesNotMatch(html, /value="10000"/)
})
