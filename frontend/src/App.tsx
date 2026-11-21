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
  const [uploadKey, setUploadKey] = useState(0)
  const [language, setLanguage] = useState<Language>('ko')
  const [stepNotice, setStepNotice] = useState('')
  const previousSection = useRef(section)
  useEffect(() => {
    if (previousSection.current !== section) {
      document.getElementById('main-content')?.focus()
      window.scrollTo({ top: 0, behavior: 'auto' })
    }
    previousSection.current = section
  }, [section])

  function navigate(next: WorkspaceSection) {
    setStepNotice('')
    if ((next === 'edit' || next === 'results') && !review && !payslip) return
    if (next === 'results' && !request && !payslipRequest) {
      setStepNotice('입력 내용을 확인하고 동의한 뒤 점검할 수 있어요.')
      setSection('edit')
      return
    }
    setSection(next)
  }
  function clearReview() {
    setReview(null); setRequest(null); setServerResult(null)
    setPayslip(null); setPayslipRequest(null); setPayslipResult(null); setStepNotice('')
  }
  function startNewDocument() {
    clearReview(); setDocumentName(null); setLanguage('ko'); setUploadKey(value => value + 1); setSection('upload')
  }
  function changeLanguage(next: Language) {
    setLanguage(next); setRequest(null); setServerResult(null); setPayslipRequest(null); setPayslipResult(null)
    setReview(current => current ? { ...current, language: next, confirmed: false, document: current.document ? { ...current.document, language: next } : null } : null)
    setPayslip(current => current ? { ...current, language: next, confirmed: false, document: { ...current.document, language: next } } : null)
  }
  function beginReview(session: ReviewSession) { clearReview(); setReview(session); setLanguage(session.language); setSection('edit') }
  function continueFromUpload(document: PreparedDocument, ocr?: OcrResult) {
    if (ocr && document.docType === 'payslip') { clearReview(); setPayslip(createPayslipSession(document, ocr.raw_text, ocr.payslip, undefined, ocr.extracted.hourly_wage.value)); setSection('edit'); return }
    beginReview(ocr ? createOcrSession(document, ocr) : createReviewSession('manual', document))
  }
  const sampleStart = (language: Language = 'ko') => beginReview({ ...createReviewSession('sample'), language })
  const activeName = payslip ? payslip.document.file.name : review ? review.document?.file.name ?? '샘플_근로계약서' : documentName

  return <AppLayout section={section} onNavigate={navigate} documentName={activeName} hasReview={!!(review || payslip)} hasRequest={!!(request || payslipRequest)} onNewDocument={startNewDocument}>
    {stepNotice && <p role="status">{stepNotice}</p>}
    <div hidden={section !== 'upload'}><DocumentUploadPage key={uploadKey} live active={section === 'upload'} hasReview={!!(review || payslip)} onResume={() => navigate('edit')} onInvalidate={clearReview} onLanguageChange={changeLanguage} onDocumentChange={setDocumentName} onContinue={continueFromUpload} onSample={sampleStart} /></div>
    {section === 'edit' && payslip ? <PayslipReviewPage session={payslip} onChange={next => { setPayslip(next); setPayslipRequest(null); setPayslipResult(null) }} onReplace={() => navigate('upload')} onConfirm={payload => { setStepNotice(''); setPayslipRequest(payload); setSection('results') }} />
      : section === 'results' && payslip && payslipRequest ? <PayslipResultsPage payload={payslipRequest} cachedResult={payslipResult} onResult={setPayslipResult} onEdit={() => setSection('edit')} />
      : section === 'edit' && review ? <DocumentReviewPage session={review} onChange={next => { setReview(next); setRequest(null); setServerResult(null) }} onReplace={() => navigate('upload')} onConfirm={payload => { setStepNotice(''); setRequest(payload); setSection('results') }} />
        : section === 'results' && request ? review?.mode === 'sample' ? <CheckResultsPage request={request} onEdit={() => setSection('edit')} onAsk={() => setSection('chat')} /> : <LiveResultsPage cachedResult={serverResult} onResult={setServerResult} payload={request} onEdit={() => setSection('edit')} />
          : section === 'chat' ? <QuestionPage language={language} onBack={request || payslipRequest ? () => navigate('results') : undefined} />
          : section === 'recordings' ? <RecordingsPage language={language} />
          : section === 'edit' || section === 'results' ? <StatePanel status="empty" title="확인할 문서를 준비해 주세요" description="문서를 선택해 직접 입력하거나 샘플 OCR 응답으로 체험할 수 있어요." action={<div className="review-empty-actions"><Button onClick={() => navigate('upload')}>문서 선택하기</Button><Button variant="secondary" onClick={() => sampleStart()}>샘플 문서로 체험하기</Button></div>} />
            : null}
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
