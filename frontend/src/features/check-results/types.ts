export type WageCalculation = {
  year: number; minimum_hourly: number; notice: string; hourly_wage: number; meets_minimum: boolean
  shortfall_per_hour: number; weekly_hours: number; weekly_holiday_eligible: boolean; weekly_holiday_hours: number; weekly_holiday_pay: number
}
export type CheckItem = { level: 'ok' | 'check'; title: string; description: string }
export type Source = { id: string; title: string; snippet?: string | null; url?: string | null }
export type ReviewResult = { calculation: WageCalculation; items: CheckItem[]; explanation?: string | null; sources: Source[]; disclaimer: string }
export type ResultScenario = 'ready' | 'no-explanation' | 'no-sources' | 'loading' | 'error'
