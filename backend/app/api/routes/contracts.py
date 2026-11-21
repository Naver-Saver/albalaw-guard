from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.core.errors import BadRequestError, FileTooLargeError, UnsupportedFileError
from app.core.response import ApiResponse, ok
from app.schemas.contracts import DocType, OcrResult, ReviewRequest, ReviewResult
from app.services import clova_ocr, review
from app.services.extract import extract_fields

router = APIRouter(prefix="/contracts", tags=["contracts"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # BR-01
ALLOWED = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "pdf": "pdf"}
CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}


def _detect_format(upload: UploadFile) -> str:
    ext = (upload.filename or "").rsplit(".", 1)[-1].lower() if "." in (upload.filename or "") else ""
    fmt = ALLOWED.get(ext) or CONTENT_TYPES.get(upload.content_type or "")
    if not fmt:
        raise UnsupportedFileError("jpg, png, pdf 파일만 올릴 수 있어요.")
    return fmt


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise FileTooLargeError("10MB 이하 파일만 올릴 수 있어요.")
    if not data:
        raise UnsupportedFileError("빈 파일이에요.")
    return data


@router.post("/ocr", response_model=ApiResponse[OcrResult])
async def ocr_contract(
    file: Annotated[UploadFile, File(description="jpg/png/pdf, 10MB 이하")],
    doc_type: Annotated[DocType, Form()] = "contract",
) -> ApiResponse[OcrResult]:
    fmt = _detect_format(file)
    content = await _read_limited(file, MAX_IMAGE_BYTES)
    try:
        text = await clova_ocr.recognize(content, fmt)
    finally:
        del content  # 원본은 메모리에서만 처리 (NFR-01)
    return ok(OcrResult(doc_type=doc_type, raw_text=text.raw_text, extracted=extract_fields(text.lines)))


@router.post("/review", response_model=ApiResponse[ReviewResult])
async def review_contract(req: ReviewRequest) -> ApiResponse[ReviewResult]:
    try:
        result = await review.review(req)
    except ValueError as e:  # 데이터 없는 연도 등 (BR-03)
        raise BadRequestError(str(e)) from e
    return ok(result)
