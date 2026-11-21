"""질문 API (API-07 음성 · API-08 텍스트, FS-03)."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.core.errors import BadRequestError, FileTooLargeError, UnsupportedFileError
from app.core.response import ApiResponse, ok
from app.schemas.ask import AskResult, AskTextRequest
from app.services import ask as ask_service
from app.services import audio, clova_csr

router = APIRouter(prefix="/ask", tags=["ask"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_SECONDS = 60  # BR-12
SECONDS_TOLERANCE = 1.0  # 녹음 종료 지연 등 오차
# 형식 확인 전의 허용 목록. 브라우저 녹음(webm·ogg)은 CSR이 읽는지 실제 확인이 필요하다.
ALLOWED_EXT = {"mp3", "wav", "m4a", "aac", "ogg", "flac", "webm"}


def _extension(upload: UploadFile) -> str:
    name = upload.filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise UnsupportedFileError("mp3, wav 같은 음성 파일만 올릴 수 있어요.")
    return ext


@router.post("/text", response_model=ApiResponse[AskResult])
async def ask_text(req: AskTextRequest) -> ApiResponse[AskResult]:
    """텍스트 질문 (API-08). FAQ면 route=faq, 아니면 근거 기반 설명 route=studio."""
    return ok(await ask_service.answer_question(req.question))


@router.post("/voice", response_model=ApiResponse[AskResult])
async def ask_voice(
    file: Annotated[UploadFile, File(description="60초 이하 음성")],
) -> ApiResponse[AskResult]:
    """음성 질문 (API-07). CSR로 글자로 바꾼 뒤 텍스트 질문과 같은 경로로 답한다.
    녹음은 저장하지 않는다. 인식된 말이 없으면 route=none 으로 '잘 못 들었어요'를 돌려준다(BR-13)."""
    ext = _extension(file)
    data = await file.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise UnsupportedFileError("빈 파일이에요.")
    if len(data) > MAX_AUDIO_BYTES:
        raise FileTooLargeError("10MB 이하 음성만 올릴 수 있어요.")
    seconds = audio.duration_seconds(data, ext)
    if seconds is not None and seconds > MAX_SECONDS + SECONDS_TOLERANCE:
        raise BadRequestError(f"{MAX_SECONDS}초 이하로 녹음해 주세요.")
    question = await clova_csr.recognize(data)
    return ok(await ask_service.answer_question(question))
