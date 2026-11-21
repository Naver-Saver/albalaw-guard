import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

const server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => server.close())
const load = () => server.ssrLoadModule('/src/features/check-results/sampleResult.ts')
const request = { hourly_wage: 50000, weekly_hours: 1, work_days: ['일'], year: 2027, lang: 'ko' }

test('sample response is fixed, independent per call and never calculated from edited inputs', async () => {
  const { getSampleResult } = await load()
  const first = getSampleResult('ready')
  assert.equal(first.calculation.year, 2026)
  assert.equal(first.calculation.hourly_wage, 10000)
  assert.equal(first.calculation.minimum_hourly, 10320)
  assert.equal(first.calculation.shortfall_per_hour, 320)
  assert.equal(first.calculation.weekly_holiday_pay, 41280)
  first.items[0].title = 'changed'
  assert.notEqual(getSampleResult('ready').items[0].title, 'changed')
})

test('missing sources suppress explanations; missing explanation preserves calculation', async () => {
  const { getSampleResult } = await load()
  const noSources = getSampleResult('no-sources')
  assert.deepEqual(noSources.sources, [])
  assert.equal(noSources.explanation, null)
  const noExplanation = getSampleResult('no-explanation')
  assert.equal(noExplanation.explanation, null)
  assert.equal(noExplanation.calculation.minimum_hourly, 10320)
  assert.ok(noExplanation.sources.length > 0)
})

test('official source links reject active content, untrusted hosts and disguised destinations', async () => {
  const { safeOfficialUrl } = await server.ssrLoadModule('/src/features/check-results/sourceUrl.ts')
  assert.ok(safeOfficialUrl('https://www.moel.go.kr/news/'))
  assert.ok(safeOfficialUrl('https://www.law.go.kr/법령/근로기준법/제55조'))
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'https://evil.example/', 'https://www.moel.go.kr.evil.example/', 'https://evil@www.moel.go.kr/', 'http://www.moel.go.kr/', undefined]) assert.equal(safeOfficialUrl(url), null)
})

test('result view separates edited request from fixed sample and includes provenance and advice', async () => {
  const { CheckResultsPage } = await server.ssrLoadModule('/src/pages/CheckResultsPage.tsx')
  const html = renderToStaticMarkup(createElement(CheckResultsPage, { request, onEdit: () => {}, onAsk: () => {} }))
  assert.match(html, /샘플 점검 결과/)
  assert.match(html, /입력값으로 계산하지 않았어요/)
  assert.match(html, /50,000/)
  assert.match(html, /2027/)
  assert.match(html, /2026/)
  assert.match(html, /10,320/)
  assert.match(html, /고용노동부/)
  assert.match(html, /법률 자문/)
  assert.match(html, /1350/)
  assert.match(html, /132/)
})

test('empty evidence never produces a fake official link or a generated answer', async () => {
  const { CheckResultsPage } = await server.ssrLoadModule('/src/pages/CheckResultsPage.tsx')
  const html = renderToStaticMarkup(createElement(CheckResultsPage, { request, onEdit: () => {}, onAsk: () => {}, initialScenario: 'no-sources' }))
  assert.match(html, /연결된 근거가 없어요/)
  assert.match(html, /10,320/)
  assert.doesNotMatch(html, /공식 원문 열기/)
  assert.doesNotMatch(html, /법률 자문이 아닌 안내 예시입니다/)
})

test('loading and error views are recoverable and do not display ready calculations', async () => {
  const { CheckResultsPage } = await server.ssrLoadModule('/src/pages/CheckResultsPage.tsx')
  for (const initialScenario of ['loading', 'error']) {
    const html = renderToStaticMarkup(createElement(CheckResultsPage, { request, onEdit: () => {}, onAsk: () => {}, initialScenario }))
    assert.doesNotMatch(html, /10,320/)
    assert.match(html, /실제 요청은 보내지 않아요/)
    if (initialScenario === 'error') assert.match(html, /다시 보기/)
  }
})
