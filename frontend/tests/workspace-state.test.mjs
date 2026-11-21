import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { Window } from 'happy-dom'
import { createServer } from 'vite'
import { act, createElement } from 'react'

const browser = new Window({ url: 'http://localhost/#/workspace' })
globalThis.window = browser
globalThis.document = browser.document
globalThis.HTMLElement = browser.HTMLElement
globalThis.IS_REACT_ACT_ENVIRONMENT = true
const originalFetch = globalThis.fetch
const originalCreate = URL.createObjectURL
const originalRevoke = URL.revokeObjectURL
URL.createObjectURL = () => 'blob:synthetic-preview'
URL.revokeObjectURL = () => {}
const { createRoot } = await import('react-dom/client')
const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
let App
before(async () => { App = (await server.ssrLoadModule('/src/App.tsx')).default })
after(async () => {
  await server.close()
  globalThis.fetch = originalFetch
  URL.createObjectURL = originalCreate
  URL.revokeObjectURL = originalRevoke
  await browser.happyDOM.close()
})

const nav = text => [...document.querySelectorAll('.nav-item')].find(el => el.textContent.includes(text))
const button = text => [...document.querySelectorAll('button')].find(el => el.textContent.includes(text))
const click = async el => { assert.ok(el, 'button exists'); await act(async () => { el.click() }) }
async function selectFile(name = 'contract.png') {
  const el = document.querySelector('input[aria-label="문서 파일 선택"]')
  Object.defineProperty(el, 'files', { configurable: true, value: [new File(['synthetic'], name, { type: 'image/png' })] })
  await act(async () => { el.dispatchEvent(new browser.Event('change', { bubbles: true })) })
}
async function mount(run) {
  const host = document.createElement('div'); document.body.append(host)
  const root = createRoot(host)
  try { await act(async () => { root.render(createElement(App)) }); await run() }
  finally { await act(async () => root.unmount()); host.remove() }
}
const field = label => {
  const el = [...document.querySelectorAll('label')].find(el => el.textContent.startsWith(label))
  return document.getElementById(el.htmlFor)
}
const editValue = async (el, value) => {
  await act(async () => {
    Object.getOwnPropertyDescriptor(browser.HTMLInputElement.prototype, 'value').set.call(el, value)
    el.dispatchEvent(new browser.Event('input', { bubbles: true }))
  })
}
function mockOcr() {
  const f = value => ({ value, confidence: 'high' })
  globalThis.fetch = async url => {
    assert.equal(url, '/api/contracts/ocr')
    return new Response(JSON.stringify({ success: true, data: { doc_type: 'contract', raw_text: 'synthetic', extracted: { hourly_wage: f(12000), weekly_hours: f(20), work_days: f(['월']), break_minutes: f(30), year: f(2026) } } }))
  }
}
async function extract() {
  await selectFile()
  await click(field('문서 처리 및 개인정보'))
  await click(button('문서 내용 추출하기'))
}

test('upload file, English selection and consent survive sidebar round trips before extraction', async () => {
  await mount(async () => {
    await selectFile()
    await click(document.querySelector('input[name="language"][value="en"]'))
    await click(field('문서 처리 및 개인정보'))
    await click(nav('질문하기')); await click(nav('문서 업로드'))
    assert.match(document.querySelector('.file-preview').textContent, /contract.png/)
    assert.equal(document.querySelector('input[value="en"]').checked, true)
    assert.equal(field('문서 처리 및 개인정보').checked, true)
  })
})

test('unavailable document steps are disabled until OCR and pending results return to editing', async () => {
  mockOcr()
  await mount(async () => {
    assert.equal(nav('확인 · 수정').disabled, true)
    assert.equal(nav('점검 결과').disabled, true)
    await extract()
    assert.equal(nav('확인 · 수정').disabled, false)
    await click(nav('점검 결과'))
    assert.equal(nav('확인 · 수정').getAttribute('aria-current'), 'page')
    assert.match(document.querySelector('main').textContent, /확인.*점검/)
  })
})

test('OCR draft survives upload/chat navigation; file replacement and explicit restart clear old work', async () => {
  mockOcr()
  await mount(async () => {
    await extract()
    await editValue(field('시급'), '13500')
    await click(nav('문서 업로드')); await click(nav('질문하기')); await click(nav('확인 · 수정'))
    assert.equal(field('시급').value, '13500')
    await click(nav('문서 업로드'))
    await click(document.querySelector('input[value="en"]'))
    await click(nav('확인 · 수정'))
    assert.equal(field('시급').value, '13500')
    await click(nav('문서 업로드')); await selectFile('replacement.png')
    assert.equal(nav('확인 · 수정').disabled, true)
    await click(button('새 문서 시작'))
    assert.equal(document.querySelector('.file-preview'), null)
    assert.equal(document.querySelector('input[value="ko"]').checked, true)
    assert.equal(nav('점검 결과').disabled, true)
  })
})

test('completed contract result is reused after navigation and language change revokes confirmation', async () => {
  const { getSampleResult } = await server.ssrLoadModule('/src/features/check-results/sampleResult.ts')
  mockOcr()
  const ocrFetch = globalThis.fetch
  let reviews = 0
  globalThis.fetch = async (url, init) => {
    if (url === '/api/contracts/review') {
      reviews++
      return new Response(JSON.stringify({ success: true, data: getSampleResult('ready') }))
    }
    return ocrFetch(url, init)
  }
  await mount(async () => {
    await extract()
    await click(field('원본과 입력 내용'))
    await click(button('확인한 내용으로 점검하기'))
    assert.match(document.querySelector('main').textContent, /입력한 내용의 점검 결과/)
    await click(nav('문서 업로드')); await click(nav('질문하기')); await click(nav('점검 결과'))
    assert.match(document.querySelector('main').textContent, /입력한 내용의 점검 결과/)
    assert.equal(reviews, 1)
    await click(nav('문서 업로드')); await click(document.querySelector('input[value="en"]'))
    await click(nav('점검 결과'))
    assert.equal(nav('확인 · 수정').getAttribute('aria-current'), 'page')
    assert.equal(field('원본과 입력 내용').checked, false)
    assert.equal(field('시급').value, '12000')
  })
})

test('leaving upload aborts OCR without losing file or allowing a late response to change menus', async () => {
  let finish
  let signal
  const f = value => ({ value, confidence: 'high' })
  globalThis.fetch = (_url, init) => {
    signal = init.signal
    return new Promise(resolve => { finish = () => resolve(new Response(JSON.stringify({ success: true, data: { doc_type: 'contract', raw_text: 'late', extracted: { hourly_wage: f(1), weekly_hours: f(1), work_days: f([]), break_minutes: f(null) } } }))) })
  }
  await mount(async () => {
    await extract()
    await click(nav('질문하기'))
    assert.equal(signal.aborted, true)
    await act(async () => { finish() })
    assert.equal(nav('질문하기').getAttribute('aria-current'), 'page')
    assert.equal(nav('확인 · 수정').disabled, true)
    await click(nav('문서 업로드'))
    assert.match(document.querySelector('.file-preview').textContent, /contract.png/)
    assert.equal(button('문서 내용 추출하기').disabled, false)
  })
})

test('payslip draft survives sidebar navigation and document type changes invalidate it', async () => {
  const f = value => ({ value, confidence: 'high' })
  globalThis.fetch = async () => new Response(JSON.stringify({ success: true, data: {
    doc_type: 'payslip', raw_text: 'synthetic payslip',
    extracted: { hourly_wage: f(12000) },
    payslip: { employee_name: '예시', pay_date: '2026-11-01', items: [{ name: '기본급', amount: 100000, source_text: '기본급' }], deductions: [], total_pay: f(100000), net_pay: f(100000), calculation_method: null },
  } }))
  await mount(async () => {
    await click(document.querySelector('input[name="document-type"][value="payslip"]'))
    await extract()
    await editValue(field('지급총액'), '110000')
    await click(nav('문서 업로드')); await click(nav('질문하기')); await click(nav('확인 · 수정'))
    assert.equal(field('지급총액').value, '110000')
    await click(nav('점검 결과'))
    assert.equal(nav('확인 · 수정').getAttribute('aria-current'), 'page')
    await click(nav('문서 업로드'))
    await click(document.querySelector('input[name="document-type"][value="contract"]'))
    assert.equal(nav('확인 · 수정').disabled, true)
    assert.equal(field('문서 처리 및 개인정보').checked, false)
  })
})
