"""환경변수 기반 설정. 실제 값은 backend/.env (git 미추적)에만 둔다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "albalaw-guard"
    app_version: str = "0.1.0"
    environment: str = "local"  # local | dev | prod
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    # DB는 사용하지 않는다 (docs/spec/04-data-model.md)

    # NCP 공통 (Object Storage 등)
    ncp_access_key: str = ""
    ncp_secret_key: str = ""
    object_storage_endpoint: str = "https://kr.object.ncloudstorage.com"
    object_storage_region: str = "kr-standard"
    object_storage_bucket: str = "albalaw-uploads"
    storage_backend: str = "auto"  # auto | ncp | memory
    upload_prefix: str = "uploads/"
    law_data_cache_sec: int = 600  # law-data/*.json 캐시 시간 (Object Storage 재조회 주기)
    law_data_key: str = "law-data/manyask-worker.json"

    # CLOVA OCR
    clova_ocr_invoke_url: str = ""
    clova_ocr_secret: str = ""

    # CLOVA Speech (장문 인식)
    clova_speech_invoke_url: str = ""
    clova_speech_secret: str = ""
    clova_speech_data_key_prefix: str = ""
    recording_max_bytes: int = 200 * 1024 * 1024
    recording_max_duration_sec: int = 10 * 60
    recording_job_ttl_sec: int = 3600

    # CLOVA Studio (API 키 nv-…, Request ID는 플레이그라운드 > 코드 보기)
    clova_studio_api_key: str = ""
    clova_studio_request_id: str = ""
    clova_studio_model: str = "HCX-005"
    clova_studio_base_url: str = "https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions"

    # CLOVA Chatbot
    clova_chatbot_invoke_url: str = ""
    clova_chatbot_secret: str = ""

    # AI·NAVER API > Application (CLOVA Speech Recognition, CLOVA Voice)
    ainaver_client_id: str = ""
    ainaver_client_secret: str = ""

    # Papago Translation > Application (별도 앱 — AI·NAVER 키로는 401)
    papago_client_id: str = ""
    papago_client_secret: str = ""

    # 공공데이터포털 서비스키
    data_go_kr_service_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
