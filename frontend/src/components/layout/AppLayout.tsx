import { useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Icon } from '../common/Icon'
import { workspaceNavigation } from './navigation'
import type { WorkspaceSection } from './navigation'
import './layout.css'

export function AppLayout({ section, onNavigate, children, documentName }: { section: WorkspaceSection; onNavigate: (section: WorkspaceSection) => void; children: ReactNode; documentName?: string | null }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLButtonElement>(null)
  const mainRef = useRef<HTMLElement>(null)
  const current = workspaceNavigation.find(item => item.id === section)!

  return <div className="app-shell" onKeyDown={event => {
    if (event.key === 'Escape' && menuOpen) { setMenuOpen(false); menuRef.current?.focus() }
  }}>
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); mainRef.current?.focus(); mainRef.current?.scrollIntoView() }}>본문으로 바로가기</a>
    <header className="app-header">
      <a href="#/" className="brand" aria-label="Saver 서비스 소개로"><span className="brand__icon"><Icon name="file" width="22" height="22" /></span>Saver</a>
      <span className="app-header__tagline">내 일의 권리를, 더 쉽게</span>
      <span className="app-header__service">알바생 노동권 지킴이</span>
      <button ref={menuRef} className="menu-toggle" type="button" aria-expanded={menuOpen} aria-controls="workspace-sidebar" onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? 'close' : 'menu'} /><span>{menuOpen ? '닫기' : '메뉴'}</span></button>
    </header>
    <div className="app-body">
      <aside id="workspace-sidebar" className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}>
        <div className="sidebar__label">WORKSPACE</div>
        <nav aria-label="작업 메뉴">{workspaceNavigation.map(item => <button key={item.id} className="nav-item" type="button" aria-current={item.id === section ? 'page' : undefined} onClick={() => { onNavigate(item.id); setMenuOpen(false); mainRef.current?.focus() }}><Icon name={item.icon} /><span>{item.label}</span></button>)}</nav>
        <div className="sidebar__document"><span className="sidebar__label">진행 중인 문서</span><div className="sidebar__document-icon"><Icon name="file" /></div><strong className="sidebar__filename">{documentName || '문서를 올려주세요'}</strong><p>{documentName ? '기기에서만 미리보기 중' : '새 문서를 기다리고 있어요'}</p></div>
        <a className="sidebar__guide" href="#/guide"><Icon name="info" /><span><strong>처음이라면, 이용 안내</strong><small>이용 방법을 차근차근 살펴보세요.</small></span></a>
        <div className="sidebar__privacy"><Icon name="shield" /><p>내 문서는 안전하게<br /><strong>처리 후 원본을 보관하지 않아요.</strong></p></div>
        <p className="sidebar__footer">Saver · 함께 지키는 일의 권리</p>
      </aside>
      <div className="workspace">
        <div className="workspace__bar"><span>내 문서</span><span className="workspace__breadcrumb">/</span><strong>{current.label}</strong><span className="preview-label">화면 미리보기</span></div>
        <main id="main-content" className="workspace__content" ref={mainRef} tabIndex={-1}>{children}</main>
        <footer className="workspace__footer"><Icon name="info" width="16" height="16" /><p>공식 Q&A를 바탕으로 확인할 부분을 안내해요. 법률 자문을 대신하지 않아요.</p></footer>
      </div>
    </div>
  </div>
}
