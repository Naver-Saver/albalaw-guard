import type { DocumentKind } from './validation'

export function createPreviewBlob(file: File, kind: DocumentKind): Blob {
  const type = kind === 'pdf' ? 'application/pdf' : file.name.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg'
  return file.slice(0, file.size, type)
}
