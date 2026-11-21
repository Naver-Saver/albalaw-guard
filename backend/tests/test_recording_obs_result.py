import pytest

from app.core.errors import AiUnavailableError
from app.services import clova_speech, recordings
from app.services.storage import get_storage


@pytest.fixture
def obs_job(settings, monkeypatch):
    recordings.clear_jobs()
    monkeypatch.setattr(settings, "clova_speech_result_prefix", "speech-results/")
    job = recordings._JobRecord(
        job_id="rec_obs", token="token-test", audio_key="uploads/rec_obs.mp3", status="processing"
    )
    recordings._jobs[job.job_id] = job
    get_storage().upload_bytes(job.audio_key, b"synthetic")

    async def completed(_):
        return clova_speech.SpeechPollResult(
            status="completed", segments=[], speakers=[], transcript="", duration_sec=0
        )

    async def timeline(_):
        return []

    monkeypatch.setattr(clova_speech, "get_recognition_status", completed)
    monkeypatch.setattr(recordings, "build_timeline", timeline)
    yield job
    recordings.clear_jobs()


async def test_completed_status_loads_obs_transcript_and_removes_original_and_result(obs_job):
    storage = get_storage()
    assert (await recordings.get_recording_job(obs_job.job_id)).status == "processing"
    key = recordings.speech_result_key(obs_job.audio_key, obs_job.token, "speech-results/")
    assert key == "speech-results/rec_obs.mp3_token-test.json"
    storage.put_json(
        key,
        {
            "token": obs_job.token,
            "segments": [
                {"start": 0, "end": 4000, "speaker": {"label": "0"}, "text": "시급을 확인해 주세요"}
            ],
        },
    )
    done = await recordings.get_recording_job(obs_job.job_id)
    assert done.status == "done"
    assert "시급을 확인해 주세요" in done.transcript
    assert done.speakers == ["화자 A"]
    assert not storage.exists(obs_job.audio_key)
    assert not storage.exists(key)


async def test_missing_obs_result_waits_then_times_out(obs_job, settings, monkeypatch):
    assert (await recordings.get_recording_job(obs_job.job_id)).status == "processing"
    assert get_storage().exists(obs_job.audio_key)
    monkeypatch.setattr(settings, "recording_result_wait_sec", 0)
    failed = await recordings.get_recording_job(obs_job.job_id)
    assert failed.status == "failed"
    assert "결과 파일" in failed.error
    assert not get_storage().exists(obs_job.audio_key)


async def test_mismatched_token_never_returns_another_transcript(obs_job):
    storage = get_storage()
    key = recordings.speech_result_key(obs_job.audio_key, obs_job.token, "speech-results/")
    storage.put_json(key, {"token": "other", "segments": []})
    with pytest.raises(AiUnavailableError):
        await recordings.get_recording_job(obs_job.job_id)
    assert storage.exists(obs_job.audio_key)
