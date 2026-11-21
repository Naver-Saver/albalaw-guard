import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
after(() => server.close())

test('direct links resolve to home, guide and workspace; unknown links recover to home', async () => {
  const { resolveRoute } = await server.ssrLoadModule('/src/navigation/routes.ts')
  assert.equal(resolveRoute(''), 'home')
  assert.equal(resolveRoute('#/'), 'home')
  assert.equal(resolveRoute('#/guide'), 'guide')
  assert.equal(resolveRoute('#/workspace'), 'workspace')
  assert.equal(resolveRoute('#/missing'), 'home')
})

test('landing offers real links to service and video guide', async () => {
  const { LandingPage } = await server.ssrLoadModule('/src/pages/LandingPage.tsx')
  const html = renderToStaticMarkup(createElement(LandingPage))
  assert.match(html, /href="#\/workspace"/)
  assert.match(html, /href="#\/guide"/)
  assert.match(html, /근로계약서/)
  assert.match(html, /예시/)
})

test('guide without supplied media shows an honest empty state and a way forward', async () => {
  const { GuidePage } = await server.ssrLoadModule('/src/pages/GuidePage.tsx')
  const html = renderToStaticMarkup(createElement(GuidePage))
  assert.doesNotMatch(html, /<video/)
  assert.match(html, /준비 중/)
  assert.match(html, /href="#\/workspace"/)
  assert.match(html, /href="#\/"/)
})

test('provided media uses native controls, captions and no autoplay', async () => {
  const { GuidePage } = await server.ssrLoadModule('/src/pages/GuidePage.tsx')
  const html = renderToStaticMarkup(createElement(GuidePage, { video: { src: '/videos/intro.mp4', captions: '/videos/intro.ko.vtt' } }))
  assert.match(html, /<video[^>]*controls/)
  assert.match(html, /src="\/videos\/intro.mp4"/)
  assert.match(html, /kind="captions"/)
  assert.doesNotMatch(html, /autoplay/i)
})
