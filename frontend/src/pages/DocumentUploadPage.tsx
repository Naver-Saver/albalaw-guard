import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Checkbox } from '../components/common/FormControls'
import { Badge } from '../components/common/Status'
import { Icon } from '../components/common/Icon'
import { DOCUMENT_ACCEPT, formatFileSize, validateDocumentFiles } from '../features/document-upload/validation'
import type { DocumentKind, DocumentType, Language } from '../features/document-upload/validation'
import { simulateExtraction } from '../features/document-upload/simulateExtraction'
import { useObjectUrl } from '../features/document-upload/useObjectUrl'
import { createPreviewBlob } from '../features/document-upload/previewBlob'
import type { PreparedDocument } from '../features/document-review/model'
import './upload.css'
import { extractDocument } from '../features/document-review/client'
import type { OcrResult } from '../features/document-review/model'

const languages: { value: Language; code: string; label: string; subtitle: string }[] = [
  { value: 'ko', code: 'KO', label: '한국어', subtitle: 'Korean' },
  { value: 'en', code: 'EN', label: 'English', subtitle: '영어' },
  { value: 'vi', code: 'VI', label: 'Tiếng Việt', subtitle: '베트남어' },
  { value: 'zh-CN', code: 'ZH', label: '中文', subtitle: '중국어' },
]

export function DocumentUploadPage({ onDocumentChange, onContinue, onSample, live = false, active = true, hasReview = false, onResume, onInvalidate, onLanguageChange }: { onDocumentChange?: (name: string | null) => void; onContinue?: (document: PreparedDocument, ocr?: OcrResult) => void; onSample?: (language: Language) => void; live?: boolean; active?: boolean; hasReview?: boolean; onResume?: () => void; onInvalidate?: () => void; onLanguageChange?: (language: Language) => void }) {
  const [language, setLanguage] = useState<Language>('ko')
  const [docType, setDocType] = useState<DocumentType>('contract')
  const [file, setFile] = useState<File | null>(null)
  const [kind, setKind] = useState<DocumentKind | null>(null)
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imageFailed, setImageFailed] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState<'idle' | 'loading' | 'done'>('idle')
  const fileInput = useRef<HTMLInputElement>(null)
  const cameraInput = useRef<HTMLInputElement>(null)
  const selectButton = useRef<HTMLButtonElement>(null)
  const requestRef = useRef<AbortController | null>(null)
  const { url: previewUrl, setPreviewFile } = useObjectUrl()
  const loading = status === 'loading'

  useEffect(() => {
    onDocumentChange?.(file?.name ?? null)
    return () => onDocumentChange?.(null)
  }, [file, onDocumentChange])
  useEffect(() => () => { requestRef.current?.abort(); requestRef.current = null }, [])
  useEffect(() => {
    if (!active && requestRef.current) resetExtraction()
  }, [active])

  function resetExtraction() {
    requestRef.current?.abort()
    requestRef.current = null
    setStatus('idle')
  }

  function selectFiles(files: File[]) {
    resetExtraction()
    onInvalidate?.()
    setConsent(false)
    setImageFailed(false)
    const result = validateDocumentFiles(files)
    setError(result.error)
    setKind(result.kind)
    setPreviewFile(result.kind ? createPreviewBlob(files[0], result.kind) : null)
    setFile(result.error ? null : files[0])
  }

  function handleInput(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    if (files.length) selectFiles(files)
    event.target.value = ''
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    selectFiles(Array.from(event.dataTransfer.files))
  }

  function removeFile() {
    resetExtraction()
    onInvalidate?.()
    setPreviewFile(null)
    setFile(null); setKind(null); setConsent(false); setError(null); setImageFailed(false)
    selectButton.current?.focus()
  }

  async function handleExtract() {
    if (!file || !kind || !consent || imageFailed || loading || requestRef.current) return
    const controller = new AbortController()
    requestRef.current = controller
    setStatus('loading')
    try {
      const ocr = live ? await extractDocument({ file, kind, docType, language }, controller.signal) : (await simulateExtraction(controller.signal), undefined)
      if (requestRef.current === controller) {
        setStatus('done')
        onContinue?.({ file, kind, docType, language }, ocr)
      }
    } catch (error) {
      if (!controller.signal.aborted && requestRef.current === controller) { setError(error instanceof Error ? error.message : '요청에 실패했어요. 다시 시도해 주세요.'); setStatus('idle') }
    } finally {
      if (requestRef.current === controller) requestRef.current = null
    }
  }

  return <>
    <div className="upload-heading"><div><p className="eyebrow">MY FIRST WORK, MY RIGHTS</p><h1>한국어 계약서, 차근차근 확인해요</h1><p>익숙한 언어와 문서 종류를 고르고, 선명한 문서 사진을 준비해 주세요.</p></div><Badge>STEP 01 · 문서 준비</Badge></div>
    <div className="upload-demo"><Icon name="info" /><p><strong>{live ? '근로계약서 OCR 연결' : '업로드 화면 미리보기'}</strong>{live ? '동의 후 추출 버튼을 누르면 파일을 서버로 전송해 글자를 읽어요. 민감한 정보는 가린 사본을 권장해요. 파일 없는 샘플 체험은 전송하지 않아요.' : '선택한 파일은 이 기기에서만 확인하며 서버로 전송되지 않아요. 추출 버튼을 체험한 뒤 원본을 보며 직접 입력할 수 있어요. 실제 OCR는 아직 연결하지 않았어요.'}</p></div>
    <div className="upload-grid">
      <div className="upload-options">
        <Card title="안내받을 언어" description="편하게 이해할 수 있는 언어를 선택해요.">
          <fieldset className="language-options"><legend className="sr-only">안내받을 언어 선택</legend>{languages.map(item => <label className="language-option" key={item.value}><input type="radio" name="language" value={item.value} checked={language === item.value} onChange={() => { setLanguage(item.value); resetExtraction(); onLanguageChange?.(item.value) }} /><span className="language-code">{item.code}</span><span><strong>{item.label}</strong><small>{item.subtitle}</small></span><span className="language-check" aria-hidden="true"><Icon name="check" width="13" height="13" /></span></label>)}</fieldset>
          <p className="upload-hint">실제 계약서 점검의 설명과 확인 항목을 선택한 언어로 번역해요. 화면 메뉴와 샘플 체험은 한국어로 표시돼요.</p>
        </Card>
        <div className="upload-help"><Icon name="shield" width="24" height="24" /><h2>내 문서, 안심하고 확인하세요</h2><p>이름·주소·계좌 등 민감한 정보가 있다면 가린 사본으로 미리보기를 확인해도 좋아요.</p><ul><li>문서 전체가 보이도록 촬영해요.</li><li>빛 반사와 흐릿한 글자는 피해 주세요.</li><li>PDF는 확인할 한 페이지로 준비해 주세요.</li></ul></div>
      </div>
      <Card title="문서 업로드" description="계약서 또는 급여명세서 파일 1개를 선택해요." className="upload-card">
        <fieldset className="document-types"><legend>어떤 문서를 확인할까요?</legend>{([{ value: 'contract', label: '근로계약서' }, { value: 'payslip', label: '급여명세서' }] as const).map(item => <label key={item.value}><input type="radio" name="document-type" value={item.value} checked={docType === item.value} onChange={() => { setDocType(item.value); resetExtraction(); setConsent(false); onInvalidate?.() }} /><span><Icon name="file" width="18" height="18" />{item.label}</span></label>)}</fieldset>
        <input ref={fileInput} type="file" accept={DOCUMENT_ACCEPT} onChange={handleInput} aria-label="문서 파일 선택" className="sr-only" tabIndex={-1} />
        <input ref={cameraInput} type="file" accept="image/jpeg,image/png" capture="environment" onChange={handleInput} aria-label="문서 카메라 촬영" className="sr-only" tabIndex={-1} />
        <div className={`file-drop ${dragging ? 'file-drop--active' : ''}`} role="group" aria-label="문서 파일 놓기" onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false) }} onDrop={handleDrop}>
          <span className="file-drop__icon"><Icon name="upload" width="28" height="28" /></span><h3>{dragging ? '여기에 문서를 놓아주세요' : file ? '다른 문서로 바꿀 수 있어요' : '문서를 여기에 놓아주세요'}</h3><p>JPG · JPEG · PNG · PDF <span>파일 1개 · 최대 10MB</span></p><div className="file-drop__actions"><Button ref={selectButton} variant="secondary" onClick={() => fileInput.current?.click()}>{file ? '다른 파일 선택' : '파일 선택하기'}</Button><Button variant="ghost" onClick={() => cameraInput.current?.click()}>카메라로 촬영</Button></div>
        </div>
        <p className="upload-hint">카메라 촬영은 지원되는 기기에서 사용할 수 있어요.</p>
        <div className="upload-error" role="alert" aria-atomic="true">{error && <><Icon name="warning" width="18" height="18" /><span>{error}</span></>}</div>
        {file && <section className="file-preview" aria-label="선택한 문서 미리보기">
          <div className="file-preview__meta"><span className="file-preview__icon"><Icon name="file" /></span><div><strong>{file.name}</strong><p>{formatFileSize(file.size)} · {kind === 'pdf' ? 'PDF' : '이미지'} · {docType === 'contract' ? '근로계약서' : '급여명세서'}</p></div><Button variant="ghost" onClick={removeFile} aria-label="선택한 문서 삭제">삭제</Button></div>
          {kind === 'image' && previewUrl && !imageFailed && <div className="image-preview"><img src={previewUrl} alt="선택한 문서 원본 미리보기" onError={() => { setImageFailed(true); setError('이미지를 미리볼 수 없어요. 파일이 손상되지 않았는지 확인하고 다른 사진을 선택해 주세요.'); resetExtraction() }} /></div>}
          {kind === 'image' && !previewUrl && <p className="upload-hint">미리보기를 준비하고 있어요.</p>}
          {kind === 'pdf' && <div className="pdf-preview"><Icon name="file" width="32" height="32" /><p>선택한 PDF 원본을 새 탭에서 확인할 수 있어요.</p>{previewUrl && <a className="button button--secondary" href={previewUrl} target="_blank" rel="noreferrer">PDF 미리보기 열기</a>}</div>}
        </section>}
        <details className="upload-privacy"><summary>문서 처리 및 개인정보 안내</summary><p>{live ? '추출 버튼을 누르면 선택한 파일을 백엔드와 OCR 서비스로 전송해 처리해요. 서버는 원본을 메모리에서 처리하며 별도 저장하지 않아요.' : '현재 미리보기에서는 파일을 브라우저 메모리에만 두고, 서버로 전송하거나 별도로 저장하지 않아요.'} 작업 메뉴를 옮겨도 파일과 입력 내용은 현재 탭의 메모리에 유지해요. 새 문서 시작·파일 교체·삭제 또는 서비스 소개로 나가면 기존 문서 작업을 비워요. 새로고침하거나 탭을 닫으면 유지되지 않아요. 새 탭으로 연 PDF는 해당 탭을 직접 닫아 주세요.</p></details>
        {hasReview && <p className="upload-hint">추출한 내용과 수정 내역이 남아 있어요. 다시 추출하면 기존 수정 내용과 결과가 초기화돼요.</p>}
        {hasReview && <Button variant="secondary" onClick={onResume}>추출 내용으로 돌아가기</Button>}
        <Checkbox label="문서 처리 및 개인정보 안내를 확인했습니다." checked={consent} disabled={!file || imageFailed} onChange={event => { setConsent(event.target.checked); resetExtraction() }} />
        <Button className="extract-button" onClick={handleExtract} disabled={!file || !consent || imageFailed} loading={loading}>{loading ? '문서 내용을 읽고 있어요' : hasReview ? '문서 다시 추출하기' : live ? '문서 내용 추출하기' : '문서 내용 추출하기 (체험)'}</Button>
        <p className={`upload-progress ${status === 'done' ? 'upload-progress--done' : ''}`} role="status" aria-live="polite">{status === 'loading' ? live ? '서버에서 문서를 읽고 있어요.' : '파일을 보내지 않고 처리 중 화면을 체험하고 있어요.' : status === 'done' ? live ? '문서 인식을 완료했어요.' : '화면 체험을 마쳤어요. 실제 문서는 전송되거나 추출되지 않았어요.' : '파일 선택과 안내 동의를 마치면 체험 버튼을 사용할 수 있어요.'}</p>
        {onSample && <Button variant="ghost" className="sample-start" onClick={() => onSample(language)}>파일 없이 샘플 문서로 체험하기</Button>}
      </Card>
    </div>
  </>
}
