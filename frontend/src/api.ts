// 백엔드 공통 응답 형식 (docs/spec/03-api-spec.md)
export type ApiError = { code: string; message: string; details?: unknown }
type Envelope<T> = { success: true; data: T } | { success: false; error: ApiError }

export class ApiRequestError extends Error {
  code: string
  constructor(err: ApiError) {
    super(err.message)
    this.code = err.code
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  const body = (await res.json().catch(() => null)) as Envelope<T> | null
  if (!body) throw new ApiRequestError({ code: 'INTERNAL_ERROR', message: `HTTP ${res.status}` })
  if (!body.success) throw new ApiRequestError(body.error)
  return body.data
}

export type Health = { status: string; version: string }

export const fetchHealth = () => request<Health>('/health')
