# NCP 인프라 스크립트

배포판 `ncloud` CLI(1.1.12)는 KVM(g3) 서버 파라미터(`serverImageNo`, `serverSpecCode`)와 `getServerSpecList`를 지원하지 않아,
같은 인증키(`~/.ncloud/configure`)로 VPC API를 직접 서명 호출하는 `ncp.py`를 사용합니다.

```bash
python3 ncp.py vserver getServerInstanceList regionCode=KR
python3 ncp.py raw GET https://ncr.apigw.ntruss.com/ncr/api/v2/repositories
```

| 스크립트 | 하는 일 |
| --- | --- |
| `00-check.sh` | 인증 확인 |
| `01-network.sh` | VPC·Subnet(기존 것 재사용 가능)·ACG(22/80/443) |
| `02-server.sh` | 배포 키 생성 → Init Script(Docker·스왑·키 등록) → 서버 생성 + 공인 IP |
| `04-object-storage.sh` | 업로드 버킷, NCR용 버킷, Container Registry 생성 |
| `init-script.sh` | 서버 최초 부팅 시 실행되는 스크립트 원본 |

- `env.sh`, `.state/`(배포 키 포함)는 git에 올라가지 않습니다.
- Object Storage 수명주기(자동 삭제)는 S3 API가 막혀 있어 콘솔에서 설정합니다.
- CLOVA OCR/Speech/Chatbot 도메인, CLOVA Studio, Cloud DB for MySQL은 콘솔에서 만듭니다.
