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
import { DocumentReviewPage } from './pages/DocumentReviewPage'
import { CheckResultsPage } from './pages/CheckResultsPage'
import { QuestionPage } from './pages/QuestionPage'
import { RecordingsPage } from './pages/RecordingsPage'
import { PendingReviewResult } from './pages/PendingReviewResult'
import { createReviewSession, createOcrSession } from './features/document-review/model'
import { LiveResultsPage } from './pages/LiveResultsPage'
import type { ReviewResult } from './features/check-results/types'
import type { ReviewRequest, ReviewSession } from './features/document-review/model'
import type { Language } from './features/document-upload/validation'
import { PayslipReviewPage } from './pages/PayslipReviewPage'
import { PayslipResultsPage } from './pages/PayslipResultsPage'
import { createPayslipSession } from './features/payslip/model'
import type { PayslipRequest, PayslipResult, PayslipSession } from './features/payslip/model'
import type { OcrResult, PreparedDocument } from './features/document-review/model'

function Workspace() {
  const [section, setSection] = useState<WorkspaceSection>('upload')
  const [documentName, setDocumentName] = useState<string | null>(null)
  const [review, setReview] = useState<ReviewSession | null>(null)
  const [request, setRequest] = useState<ReviewRequest | null>(null)
  const [serverResult, setServerResult] = useState<ReviewResult | null>(null)
  const [payslip, setPayslip] = useState<PayslipSession | null>(null)
  const [payslipRequest, setPayslipRequest] = useState<PayslipRequest | null>(null)
  const [payslipResult, setPayslipResult] = useState<PayslipResult | null>(null)
  const previousSection = useRef(section)
  useEffect(() => {
    if (previousSection.current !== section) {
      document.getElementById('main-content')?.focus()
      window.scrollTo({ top: 0, behavior: 'auto' })
    }
    previousSection.current = section
  }, [section])

  function navigate(next: WorkspaceSection) {
    if (next === 'upload') { setReview(null); setRequest(null); setServerResult(null); setDocumentName(null); setPayslip(null); setPayslipRequest(null); setPayslipResult(null) }
    setSection(next)
  }
  function beginReview(session: ReviewSession) { setReview(session); setRequest(null); setPayslip(null); setSection('edit') }
  function continueFromUpload(document: PreparedDocument, ocr?: OcrResult) {
    if (ocr && document.docType === 'payslip') { setReview(null); setPayslip(createPayslipSession(document, ocr.raw_text, ocr.payslip, undefined, ocr.extracted.hourly_wage.value)); setPayslipRequest(null); setPayslipResult(null); setSection('edit'); return }
    beginReview(ocr ? createOcrSession(document, ocr) : createReviewSession('manual', document))
  }
  const sampleStart = (language: Language = 'ko') => beginReview({ ...createReviewSession('sample'), language })
  const activeName = payslip ? payslip.document.file.name : review ? review.document?.file.name ?? '샘플_근로계약서' : documentName

  return <AppLayout section={section} onNavigate={navigate} documentName={activeName}>
    {section === 'upload' ? <DocumentUploadPage live onDocumentChange={setDocumentName} onContinue={continueFromUpload} onSample={sampleStart} />
      : section === 'edit' && payslip ? <PayslipReviewPage session={payslip} onChange={next => { setPayslip(next); setPayslipRequest(null); setPayslipResult(null) }} onReplace={() => navigate('upload')} onConfirm={payload => { setPayslipRequest(payload); setSection('results') }} />
      : section === 'results' && payslip && payslipRequest ? <PayslipResultsPage payload={payslipRequest} cachedResult={payslipResult} onResult={setPayslipResult} onEdit={() => setSection('edit')} />
      : section === 'edit' && review ? <DocumentReviewPage session={review} onChange={next => { setReview(next); setRequest(null); setServerResult(null) }} onReplace={() => navigate('upload')} onConfirm={payload => { setRequest(payload); setSection('results') }} />
        : section === 'results' && request ? review?.mode === 'sample' ? <CheckResultsPage request={request} onEdit={() => setSection('edit')} onAsk={() => setSection('chat')} /> : <LiveResultsPage cachedResult={serverResult} onResult={setServerResult} payload={request} onEdit={() => setSection('edit')} />
          : section === 'chat' ? <QuestionPage language={review?.language ?? payslip?.language ?? 'ko'} onBack={request ? () => setSection('results') : undefined} />
          : section === 'recordings' ? <RecordingsPage language={review?.language ?? payslip?.language ?? 'ko'} />
          : section === 'results' && review ? <PendingReviewResult onReview={() => setSection('edit')} />
          : section === 'edit' || section === 'results' ? <StatePanel status="empty" title="확인할 문서를 준비해 주세요" description="문서를 선택해 직접 입력하거나 샘플 OCR 응답으로 체험할 수 있어요." action={<div className="review-empty-actions"><Button onClick={() => navigate('upload')}>문서 선택하기</Button><Button variant="secondary" onClick={() => sampleStart()}>샘플 문서로 체험하기</Button></div>} />
            : <StatePanel status="empty" title="아직 준비 중인 화면이에요" description="질문 기능은 다음 단계에서 연결해요. 지금은 문서 입력과 샘플 결과를 살펴볼 수 있어요." action={request ? <Button variant="secondary" onClick={() => setSection('results')}>샘플 결과로 돌아가기</Button> : <Button onClick={() => navigate('upload')}>문서 업로드로</Button>} />}
  </AppLayout>
}

export default function App() {
  const route = useRoute()
  const previousRoute = useRef(route)
  useEffect(() => {
    document.title = `${route === 'home' ? '내 첫 알바, Saver' : route === 'guide' ? '계약서 교육 | Saver' : '내 문서 | Saver'} · 알바생 노동권 지킴이`
    if (previousRoute.current !== route) {
      document.getElementById(route === 'workspace' ? 'main-content' : 'public-content')?.focus()
      window.scrollTo({ top: 0, behavior: 'auto' })
    }
    previousRoute.current = route
  }, [route])
  if (route !== 'workspace') return <PublicLayout page={route}>{route === 'home' ? <LandingPage /> : <GuidePage />}</PublicLayout>
  return <Workspace />
}
