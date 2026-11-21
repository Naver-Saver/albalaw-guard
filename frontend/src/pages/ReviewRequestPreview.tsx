import { Button } from '../components/common/Button'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Status'
import { Icon } from '../components/common/Icon'
import type { ReviewRequest } from '../features/document-review/model'

export function ReviewRequestPreview({ request, onBack }: { request: ReviewRequest; onBack: () => void }) {
  return <>
    <div className="review-heading"><div><p className="eyebrow">REVIEW INPUT PREVIEW</p><h1>입력 내용을 확인했어요</h1><p>실제 점검을 요청하기 전, 확인한 값을 살펴보세요.</p></div><Badge>입력 확인 체험</Badge></div>
    <div className="review-notice"><Icon name="info" /><p><strong>실제 점검 결과가 아니에요</strong>아래는 확인한 입력값이에요. 계산·법령 조회·AI 설명 요청은 아직 보내지 않았어요.</p></div>
    <Card title="확인한 입력값" description="금액이나 조건의 충족 여부를 판단한 결과가 아니에요."><dl className="request-preview"><div><dt>시급</dt><dd>{request.hourly_wage.toLocaleString('ko-KR')}원</dd></div><div><dt>주 근무시간</dt><dd>{request.weekly_hours}시간</dd></div><div><dt>근무요일</dt><dd>{request.work_days.join(' · ') || '미입력'}</dd></div><div><dt>하루 휴게시간</dt><dd>{request.break_minutes === undefined ? '미입력' : `${request.break_minutes}분`}</dd></div><div><dt>적용 연도</dt><dd>{request.year}년</dd></div></dl><Button variant="secondary" onClick={onBack}>내용 다시 수정하기</Button></Card>
  </>
}
