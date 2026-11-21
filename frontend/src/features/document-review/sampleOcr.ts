import type { OcrResult } from './model'

export const SAMPLE_OCR: OcrResult = {
  doc_type: 'contract',
  raw_text: '화면 체험용 근로계약서\n시급 10,000원\n근무요일 월~금\n주 소정근로시간 20시간\n휴게시간 미기재',
  extracted: {
    hourly_wage: { value: 10000, confidence: 'high', source_text: '시급 10,000원' },
    weekly_hours: { value: 20, confidence: 'low', source_text: '주 소정근로시간 20시간' },
    work_days: { value: ['월', '화', '수', '목', '금'], confidence: 'high', source_text: '근무요일 월~금' },
    break_minutes: { value: null, confidence: 'low', source_text: '휴게시간 미기재' },
  },
}
