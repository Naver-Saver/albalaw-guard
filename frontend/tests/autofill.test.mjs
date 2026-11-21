import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'

const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
const doc = docType => ({ file: new File(['x'], 'a.png', { type: 'image/png' }), kind: 'image', docType, language: 'ko' })
const field = (value, confidence = 'high', source_text = null) => ({ value, confidence, source_text })

test('#65 OCR values go straight into the matching inputs, including the contract year', async () => {
  const { createOcrSession, extractedFor } = await server.ssrLoadModule('/src/features/document-review/model.ts')
  const ocr = { doc_type: 'contract', raw_text: '...', extracted: {
    hourly_wage: field(10320, 'low', '시간(일, 월)급: 10,320원'), weekly_hours: field(16.5, 'low'), work_days: field(['월', '수', '금']),
    break_minutes: field(30), year: field(2026, 'high', '1. 근로계약기간 : 2026년 3월 2일부터'),
  } }
  const s = createOcrSession(doc('contract'), ocr)
  assert.deepEqual(s.draft, { hourly_wage: '10320', weekly_hours: '16.5', work_days: ['월', '수', '금'], break_minutes: '30', year: '2026' })
  assert.equal(extractedFor(s.ocr, 'year').source_text, '1. 근로계약기간 : 2026년 3월 2일부터')
  // 예전 응답(year 없음)은 올해로 채우고 '직접 입력' 취급
  const old = createOcrSession(doc('contract'), { ...ocr, extracted: { ...ocr.extracted, year: undefined } })
  assert.equal(old.draft.year, String(new Date().getFullYear()))
  assert.equal(extractedFor(old.ocr, 'year'), null)
})

test('#66 payslip OCR fills editable lines and builds the API-14 request', async () => {
  const { createPayslipSession, validatePayslipDraft, toPayslipRequest } = await server.ssrLoadModule('/src/features/payslip/model.ts')
  const ocr = { employee_name: '홍길동', pay_date: '2026. 5. 10.', calculation_method: '시급 10,320원 × 96시간',
    items: [{ name: '기본급', amount: 990720, source_text: '기본급 990,720' }, { name: '주휴수당', amount: 165120, source_text: '주휴수당 165,120' }],
    deductions: [{ name: '고용보험', amount: 10400, source_text: '고용보험 10,400' }],
    total_pay: field(1155840), net_pay: field(1145440) }
  const s = createPayslipSession(doc('payslip'), 'raw', ocr, 2025)
  assert.equal(s.draft.year, '2026') // 지급일 연도 우선
  assert.deepEqual(s.draft.items.map(l => [l.name, l.amount]), [['기본급', '990720'], ['주휴수당', '165120']])
  assert.equal(s.draft.total_pay, '1155840')
  assert.deepEqual(validatePayslipDraft(s.draft), {})
  assert.throws(() => toPayslipRequest(s)) // 원본 확인 동의 필수
  const body = toPayslipRequest({ ...s, confirmed: true, draft: { ...s.draft, deductions: [...s.draft.deductions, { name: '', amount: '' }], hourly_wage: '10,320' } })
  assert.deepEqual(body.deductions, [{ name: '고용보험', amount: 10400 }])
  assert.equal(body.hourly_wage, 10320)
  assert.equal(body.employee_name, '홍길동')
  assert.equal('weekly_hours' in body, false)
  assert.ok(validatePayslipDraft({ ...s.draft, items: [{ name: '기본급', amount: '-1' }] }).items)
  assert.equal(createPayslipSession(doc('payslip'), 'raw', ocr, 2026, 10320).draft.hourly_wage, '10320') // 계산방법의 시급도 채움
  const empty = createPayslipSession(doc('payslip'), 'raw', null, 2026)
  assert.equal(empty.draft.items.length, 1)
  assert.ok(validatePayslipDraft(empty.draft).items)
})

test('law and payslip clients call the documented endpoints', async () => {
  const law = await server.ssrLoadModule('/src/features/law/client.ts')
  const pay = await server.ssrLoadModule('/src/features/payslip/client.ts')
  const original = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return new Response(JSON.stringify({ success: true, data: {} })) }
  try {
    await law.fetchMinimumWage(2027)
    await law.fetchLawSource('law-001872-55')
    await pay.reviewPayslip({ items: [], deductions: [], year: 2026, lang: 'ko' }, new AbortController().signal)
    assert.deepEqual(calls.map(c => c.url), ['/api/wage/minimum?year=2027', '/api/law/sources/law-001872-55', '/api/payslips/review'])
    assert.equal(calls[2].init.method, 'POST')
  } finally { globalThis.fetch = original }
})
