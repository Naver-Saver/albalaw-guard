"""녹음 업로드 및 비동기 대화 정리 API 라우터 (API-05 · API-06)."""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.core.response import ApiResponse, ok
from app.schemas.recordings import RecordingJob
from app.services import recordings

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post("", status_code=202, response_model=ApiResponse[RecordingJob])
async def create_recording(
    file: Annotated[UploadFile, File()],
    consent: Annotated[bool, Form()],
) -> ApiResponse[RecordingJob]:
    """녹음 파일을 업로드하고 CLOVA Speech 장문 인식 작업을 시작한다."""
    job = await recordings.create_recording_job(file=file, consent=consent)
    return ok(job)


@router.get("/{job_id}", response_model=ApiResponse[RecordingJob])
async def get_recording(job_id: str) -> ApiResponse[RecordingJob]:
    """장문 인식 작업 상태 및 완료된 화자 분리 타임라인을 조회한다."""
    job = await recordings.get_recording_job(job_id)
    return ok(job)
