"""공통 오류 정의. 오류 코드는 docs/spec/03-api-spec.md '오류 코드' 표와 같아야 한다."""

from typing import Any


class AppError(Exception):
    """서비스 코드에서 던지는 예외. 전역 핸들러가 공통 오류 응답으로 바꾼다."""

    code = "INTERNAL_ERROR"
    status_code = 500
    default_message = "잠시 후 다시 시도해 주세요."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    code = "BAD_REQUEST"
    status_code = 400
    default_message = "요청을 처리할 수 없어요."


class UnsupportedFileError(AppError):
    code = "UNSUPPORTED_FILE"
    status_code = 400
    default_message = "지원하지 않는 파일 형식이에요."


class FileTooLargeError(AppError):
    code = "FILE_TOO_LARGE"
    status_code = 413
    default_message = "파일이 너무 커요."


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    default_message = "요청한 정보를 찾을 수 없어요."


class OcrFailedError(AppError):
    code = "OCR_FAILED"
    status_code = 502
    default_message = "글자를 읽지 못했어요. 밝은 곳에서 다시 찍거나 직접 입력해 주세요."


class AiUnavailableError(AppError):
    code = "AI_UNAVAILABLE"
    status_code = 502
    default_message = "AI 설명을 불러오지 못했어요."


class ServiceNotConfiguredError(AppError):
    code = "SERVICE_NOT_CONFIGURED"
    status_code = 503
    default_message = "서비스 설정이 아직 완료되지 않았어요."
