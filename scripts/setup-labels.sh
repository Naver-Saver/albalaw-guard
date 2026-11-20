#!/usr/bin/env bash
# 사용: scripts/setup-labels.sh <owner/repo>   (gh auth login 필요)
set -euo pipefail
REPO="${1:?owner/repo}"
while IFS='|' read -r name color desc; do
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" --force
done <<'LABELS'
area: frontend|1d76db|화면·업로드·마이크·결과 표시
area: backend|0e8a16|서버·API·스토리지·배포
area: ai|8250df|OCR·Speech·Studio·Chatbot·Voice·Papago
area: data|fbca04|공공 API·FAQ·Dubbing·발표자료
type: feature|a2eeef|새 기능
type: bug|d73a4a|버그
type: docs|0075ca|문서
priority: P0|b60205|핵심 시연 흐름
priority: P1|d93f0b|확장 기능
priority: P2|fef2c0|여유 있으면
LABELS
