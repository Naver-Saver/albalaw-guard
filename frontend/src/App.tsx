import { useState } from 'react'
import { AppLayout } from './components/layout/AppLayout'
import type { WorkspaceSection } from './components/layout/navigation'
import { CommonUiPreview } from './pages/CommonUiPreview'

export default function App() {
  const [section, setSection] = useState<WorkspaceSection>('upload')
  return <AppLayout section={section} onNavigate={setSection}><CommonUiPreview /></AppLayout>
}
