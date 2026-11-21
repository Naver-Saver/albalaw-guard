import { useRef } from 'react'
import type { ReactNode } from 'react'
import { Icon } from '../common/Icon'
import { ButtonLink } from '../common/ButtonLink'
import './public.css'

export function PublicLayout({ page, children }: { page: 'home' | 'guide'; children: ReactNode }) {
  const mainRef = useRef<HTMLElement>(null)

  return <div className="public-shell">
    <a className="skip-link" href="#public-content" onClick={event => { event.preventDefault(); mainRef.current?.focus(); mainRef.current?.scrollIntoView() }}>본문으로 바로가기</a>
    <header className="public-header"><div className="public-header__inner">
      <a className="brand" href="#/" aria-label="Saver 서비스 소개로"><span className="brand__icon"><Icon name="file" width="22" height="22" /></span>Saver</a>
      <span className="public-header__tagline">내 일의 권리를, 더 쉽게</span>
      <nav aria-label="서비스 안내"><a className="public-header__guide" href={page === 'home' ? '#/guide' : '#/'}>{page === 'home' ? '이용 안내' : '서비스 소개'}</a><ButtonLink href="#/workspace">서비스 이용하기</ButtonLink></nav>
    </div></header>
    <main id="public-content" className="public-main" tabIndex={-1} ref={mainRef}>{children}</main>
    <footer className="public-footer"><div><span className="public-footer__brand">Saver</span><span>알바생 노동권 지킴이</span></div><p>정부 공식 Q&A를 바탕으로 확인할 부분을 안내해요. 법률 자문을 대신하지 않아요.</p></footer>
  </div>
}
