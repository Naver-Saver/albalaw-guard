import { request } from '../../api'

export type MinimumWage = { year: number; hourly_wage: number; period_start: string; period_end: string; is_fallback: boolean }
export type LawSource = { id: string; source: string; title: string; text: string; url: string; related_article_ids: string[] }

export function fetchMinimumWage(year: number, signal?: AbortSignal) {
  return request<MinimumWage>(`/wage/minimum?year=${encodeURIComponent(year)}`, { signal })
}
export function fetchLawSource(id: string, signal?: AbortSignal) {
  return request<LawSource>(`/law/sources/${encodeURIComponent(id)}`, { signal })
}
