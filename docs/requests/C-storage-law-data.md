# 요청: 담당 C — Object Storage 모듈 구현 후 연동 (대기 메모)

작성: 파트 A / 2026-11-21

`app/clients/storage.py`가 구현되면 알려 주세요. 그때 A가 아래 두 곳을 연결합니다.

1. `backend/sync/*.py`의 업로드 (`law-data/law-articles.json`, `qna-manual.json`, `min-wage.json`, `meta/sync_log.json`). 지금은 `--dry-run`(로컬 `backend/data/law-data/` 저장)만 동작합니다.
2. `backend/app/services/law_data.py`의 `read_json` — 지금은 로컬 폴더를 읽고, Object Storage 읽기로 교체합니다 (`# STUB` 표시된 부분).

필요한 인터페이스 (C가 정하는 대로 맞춥니다):

- 객체 읽기: `get_json(key) -> dict` 또는 바이트 읽기
- 객체 쓰기: `put_json(key, payload)` (비공개 버킷, `law-data/` 아래)

버킷 이름과 엔드포인트는 `.env.example` 기준(`albalaw-uploads`, `https://kr.object.ncloudstorage.com`)입니다.

---

## 처리 완료 (파트 C / 2026-11-21)

- **공통 모듈 경로**: `backend/app/services/storage.py` (`get_storage()`, `StorageKeys`, `get_json`, `put_json`)
- **로더 연동 (`backend/app/services/law_data.py`)**: `LAW_DATA_DIR`가 미지정일 때 `get_storage().get_json("law-data/<name>")`를 우선 조회하고, 미존재·오류 시 로컬 `backend/data/law-data/`로 fallback.
- **수집 업로드 연동 (`backend/sync/{common,wage,law,all}.py`)**: `--dry-run` 없이 실행 시 NCP Object Storage(`law-data/min-wage.json`, `law-data/law-articles.json`, `law-data/qna-manual.json`, `meta/sync_log.json`)에 직접 업로드.
