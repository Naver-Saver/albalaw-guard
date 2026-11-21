export const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
export const DOCUMENT_ACCEPT = '.jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf'
export type DocumentKind = 'image' | 'pdf'
export type DocumentType = 'contract' | 'payslip'
export type Language = 'ko' | 'en' | 'vi' | 'zh-CN'
type FileCandidate = Pick<File, 'name' | 'size' | 'type'>
type Validation = { error: null; kind: DocumentKind } | { error: string; kind: null }

export function validateDocumentFiles(files: readonly FileCandidate[]): Validation {
  const fail = (error: string): Validation => ({ error, kind: null })
  if (files.length === 0) return fail('문서 파일을 선택해 주세요.')
  if (files.length !== 1) return fail('문서는 한 번에 1개만 선택해 주세요.')
  const file = files[0]
  if (!file.size) return fail('빈 파일은 사용할 수 없어요. 다른 파일을 선택해 주세요.')
  if (file.size > MAX_DOCUMENT_BYTES) return fail('10MB 이하 파일만 올릴 수 있어요.')
  const extension = file.name.split('.').pop()?.toLowerCase()
  const expectedMime = extension === 'jpg' || extension === 'jpeg' ? 'image/jpeg' : extension === 'png' ? 'image/png' : extension === 'pdf' ? 'application/pdf' : null
  if (!expectedMime || !file.name.includes('.')) return fail('JPG, JPEG, PNG, PDF 파일을 선택해 주세요.')
  if (file.type && file.type.toLowerCase() !== expectedMime) return fail('파일 이름과 형식이 맞지 않아요. JPG, PNG, PDF 원본을 다시 선택해 주세요.')
  return { error: null, kind: expectedMime === 'application/pdf' ? 'pdf' : 'image' }
}

export function formatFileSize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.ceil(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
