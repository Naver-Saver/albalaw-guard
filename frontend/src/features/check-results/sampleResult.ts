import type { ResultScenario, ReviewResult } from './types'

// Fixed API-04 response fixture based on docs/spec/03-api-spec.md.
// Never takes the user's input and never calculates wages on the frontend.
const SAMPLE_RESULT: ReviewResult = {
  calculation: {
    year: 2026, minimum_hourly: 10320, notice: '고용노동부 고시 제2025-47호 · 2026년 적용',
    hourly_wage: 10000, meets_minimum: false, shortfall_per_hour: 320,
    weekly_hours: 20, weekly_holiday_eligible: true, weekly_holiday_hours: 4, weekly_holiday_pay: 41280,
  },
  items: [
    { level: 'check', title: '시급의 차이를 확인해 보세요', description: '샘플 계약 시급은 10,000원이고 샘플 기준 시급과 시간당 320원 차이가 있어요. 실제 문서의 적용 조건은 별도로 확인해야 해요.' },
    { level: 'check', title: '주휴수당 반영 여부를 확인해 보세요', description: '샘플 응답에는 주휴시간 4시간, 주휴수당 41,280원이 표시돼요. 실제 대상 여부는 출근 상황 등 적용 조건을 함께 확인해야 해요.' },
    { level: 'ok', title: '샘플의 적용 연도를 표시했어요', description: '이 예시의 적용 연도는 2026년이에요. 다른 연도의 입력값을 이 결과로 판단하지 마세요.' },
  ],
  explanation: '법률 자문이 아닌 안내 예시입니다. 샘플 응답에서 확인할 항목을 읽고 계약서와 급여명세서의 내용을 비교해 보세요. 실제 판단에 필요한 조건은 공식 원문과 상담을 통해 확인해 주세요.',
  sources: [
    { id: 'demo-moel-2026', title: '고용노동부 · 2026년 적용 최저임금 고시 안내', snippet: '2026년 적용 시급을 확인할 수 있는 공식 보도자료입니다. 아래 링크는 실제 문서의 분석 근거를 조회한 결과가 아니라 참고 자료 예시예요.', url: 'https://www.moel.go.kr/news/enews/report/enewsView.do?bbs_id=12&news_seq=18144' },
    { id: 'demo-law-55', title: '국가법령정보센터 · 근로기준법 제55조', snippet: '휴일에 관한 조문의 공식 원문입니다. 이 조문만으로 개별 근로자의 주휴수당 대상 여부를 판단하지 않아요.', url: 'https://www.law.go.kr/법령/근로기준법/제55조' },
  ],
  disclaimer: '이 화면은 법률 자문이 아니며, 실제 문서에 대한 점검 결과가 아닙니다. 적용 조건과 정확한 판단은 고용노동부(1350) 또는 대한법률구조공단(132)에 상담해 주세요.',
}

export function getSampleResult(scenario: ResultScenario = 'ready'): ReviewResult {
  const result = structuredClone(SAMPLE_RESULT)
  if (scenario === 'no-explanation') result.explanation = null
  if (scenario === 'no-sources') { result.sources = []; result.explanation = null }
  return result
}
