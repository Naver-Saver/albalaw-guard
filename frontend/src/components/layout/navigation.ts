import type { IconName } from '../common/Icon'

export const workspaceNavigation = [
  { id: 'upload', label: '언어 선택 · 문서 업로드', icon: 'upload' },
  { id: 'edit', label: '추출 내용 확인 · 수정', icon: 'edit' },
  { id: 'results', label: '점검 결과 · 공식 근거', icon: 'shield' },
  { id: 'chat', label: '질문하기', icon: 'chat' },
  { id: 'recordings', label: '녹음 파일 · 텍스트 변환', icon: 'audio' },
] as const satisfies ReadonlyArray<{ id: string; label: string; icon: IconName }>

export type WorkspaceSection = typeof workspaceNavigation[number]['id']
