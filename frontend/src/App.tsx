import { useEffect, useRef, useState } from 'react'
import { AppLayout } from './components/layout/AppLayout'
import type { WorkspaceSection } from './components/layout/navigation'
import { DocumentUploadPage } from './pages/DocumentUploadPage'
import { StatePanel } from './components/common/Status'
import { Button } from './components/common/Button'
import { PublicLayout } from './components/layout/PublicLayout'
import { LandingPage } from './pages/LandingPage'
import { GuidePage } from './pages/GuidePage'
import { useRoute } from './navigation/useRoute'

function Workspace() {
  const [section, setSection] = useState<WorkspaceSection>('upload')
  const [documentName, setDocumentName] = useState<string | null>(null)
  return <AppLayout section={section} onNavigate={setSection} documentName={documentName}>{section === 'upload' ? <DocumentUploadPage onDocumentChange={setDocumentName} /> : <StatePanel status="empty" title="아직 준비 중인 화면이에요" description="현재는 문서 선택과 미리보기를 사용할 수 있어요." action={<Button onClick={() => setSection('upload')}>문서 업로드로</Button>} />}</AppLayout>
}

export default function App() {
  const route = useRoute()
  const previousRoute = useRef(route)
  useEffect(() => {
    document.title = `${route === 'home' ? '내 첫 알바, Saver' : route === 'guide' ? '이용 안내 | Saver' : '내 문서 | Saver'} · 알바생 노동권 지킴이`
    if (previousRoute.current !== route) {
      document.getElementById(route === 'workspace' ? 'main-content' : 'public-content')?.focus()
      window.scrollTo({ top: 0, behavior: 'auto' })
    }
    previousRoute.current = route
  }, [route])
  if (route !== 'workspace') return <PublicLayout page={route}>{route === 'home' ? <LandingPage /> : <GuidePage />}</PublicLayout>
  return <Workspace />
}
