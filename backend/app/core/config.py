"""환경변수 기반 설정. 실제 값은 backend/.env (git 미추적)에만 둔다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "albalaw-guard"
    app_version: str = "0.1.0"
    environment: str = "local"  # local | dev | prod
    cors_origins: list[str] = ["http://localhost:5173"]

    # DB (Cloud DB for MySQL)
    database_url: str = "sqlite:///./local.db"

    # NCP 공통 (Object Storage 등)
    ncp_access_key: str = ""
    ncp_secret_key: str = ""
    object_storage_endpoint: str = "https://kr.object.ncloudstorage.com"
    object_storage_bucket: str = ""

    # CLOVA OCR
    clova_ocr_invoke_url: str = ""
    clova_ocr_secret: str = ""

    # CLOVA Speech (장문 인식)
    clova_speech_invoke_url: str = ""
    clova_speech_secret: str = ""

    # CLOVA Studio
    clova_studio_api_key: str = ""

    # CLOVA Chatbot
    clova_chatbot_invoke_url: str = ""
    clova_chatbot_secret: str = ""

    # NAVER Cloud AI·NAVER API (Papago, CSR, Voice) — API Gateway 키
    ncp_apigw_client_id: str = ""
    ncp_apigw_client_secret: str = ""

    # 공공데이터포털 서비스키
    data_go_kr_service_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
