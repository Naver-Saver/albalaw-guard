import { Button } from '../components/common/Button'
import { StatePanel } from '../components/common/Status'

export function PendingReviewResult({ onReview }: { onReview: () => void }) {
  return <StatePanel status="empty" title="추출한 내용을 먼저 확인해 주세요" description="문서는 이미 준비돼 있어요. 시급·주 근무시간 등 필수값을 확인하고, 원본 확인에 동의한 뒤 ‘확인한 내용으로 점검하기’를 눌러 주세요. 문서를 다시 선택할 필요는 없어요." action={<Button onClick={onReview}>추출 내용 확인으로 돌아가기</Button>} />
}
