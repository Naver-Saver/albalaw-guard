# NCP 인프라 스크립트 (ncloud CLI)

로컬 PC에서 순서대로 실행합니다. 자세한 흐름은 [`docs/DEPLOY.md`](../../docs/DEPLOY.md).

| 스크립트 | 하는 일 |
| --- | --- |
| `00-check.sh` | CLI 설치·인증 확인 |
| `01-network.sh` | VPC, Public Subnet, ACG(22/80/443), 로그인 키 생성 + 이미지/스펙 목록 출력 |
| `02-server.sh` | 서버 생성, 공인 IP 할당 |
| `03-server-init.sh` | **서버 안에서** Docker 설치, CD용 SSH 키 등록 |
| `04-object-storage.sh` | 업로드 버킷 + 1일 자동 삭제 규칙 |

- `env.sh`, `.state/`(로그인 키 포함)는 git에 올라가지 않습니다.
- Container Registry, CLOVA OCR/Speech/Chatbot 도메인, CLOVA Studio, Cloud DB for MySQL은 콘솔에서 만듭니다 (CLI 미지원 또는 설정 항목이 많음).
- 스크립트는 ncloud CLI의 VPC API 기준으로 작성했고, 최초 실행 시 각 단계 출력을 확인하면서 진행하세요.
