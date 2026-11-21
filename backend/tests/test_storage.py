"""Object Storage 공통 모듈 단위 테스트."""

from __future__ import annotations

import io
from typing import Any

import pytest
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.services.storage import (
    InMemoryObjectStorage,
    NcpObjectStorage,
    StorageKeys,
    create_storage,
    get_storage,
    set_storage,
)


class _FakeS3Client:
    """boto3 S3 클라이언트 동작을 모사하는 인메모리 테스트 더블."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.objects: dict[tuple[str, str], bytes] = {}

    @staticmethod
    def _not_found(operation: str) -> ClientError:
        return ClientError(
            {
                "Error": {"Code": "NoSuchKey", "Message": "Not Found"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            operation,
        )

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("put_object", kwargs))
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = bytes(kwargs["Body"])
        return {"ETag": '"fake-etag"'}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("get_object", kwargs))
        key = (kwargs["Bucket"], kwargs["Key"])
        if key not in self.objects:
            raise self._not_found("GetObject")
        return {"Body": io.BytesIO(self.objects[key])}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("head_object", kwargs))
        key = (kwargs["Bucket"], kwargs["Key"])
        if key not in self.objects:
            raise self._not_found("HeadObject")
        return {"ContentLength": len(self.objects[key])}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("delete_object", kwargs))
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)
        return {}

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("list_objects_v2", kwargs))
        bucket = kwargs["Bucket"]
        prefix = kwargs.get("Prefix", "")
        matching = sorted(k for (b, k) in self.objects if b == bucket and k.startswith(prefix))
        return {"Contents": [{"Key": k} for k in matching], "IsTruncated": False}


def test_storage_keys_formatting():
    assert StorageKeys.LAW_DATA_DEFAULT == "law-data/manyask-worker.json"
    assert StorageKeys.LAW_QNA == "law/qna_labor.json"
    assert StorageKeys.upload_recording("rec_1", ".WAV") == "uploads/rec_1.wav"
    assert StorageKeys.upload_recording("rec_1", "mp3", "") == "rec_1.mp3"
    assert StorageKeys.upload_audio("conv-1", "M4A") == "uploads/audio/conv-1.m4a"
    assert StorageKeys.speech_result("conv-1") == "results/speech/conv-1.json"
    assert StorageKeys.report_result("r-1") == "results/report/r-1.json"


def test_in_memory_storage_crud_and_idempotent_delete():
    storage = InMemoryObjectStorage()
    key = StorageKeys.upload_recording("rec_abc", "wav")

    assert not storage.exists(key)
    assert storage.get_json(key) is None
    storage.delete(key)

    storage.put_json(key, {"job_id": "rec_abc", "status": "done"})
    assert storage.exists(key)
    assert storage.get_json(key) == {"job_id": "rec_abc", "status": "done"}
    assert storage.list_keys("uploads/") == [key]

    storage.delete(key)
    assert not storage.exists(key)
    assert storage.list_keys("uploads/") == []


def test_ncp_storage_private_upload_and_not_found_handling():
    fake_client = _FakeS3Client()
    storage = NcpObjectStorage(
        bucket="albalaw-uploads",
        endpoint_url="https://kr.object.ncloudstorage.com",
        region_name="kr-standard",
        access_key="ak",
        secret_key="sk",
        client=fake_client,
    )

    assert not storage.exists("uploads/missing.wav")
    assert storage.get_bytes("uploads/missing.wav") is None
    assert storage.get_json("uploads/missing.json") is None
    storage.delete("uploads/missing.wav")

    audio_key = StorageKeys.upload_recording("rec_1", "wav")
    storage.upload_bytes(audio_key, b"RIFFDATA", content_type="audio/wav")
    put_call = next(kwargs for op, kwargs in fake_client.calls if op == "put_object")
    assert "ACL" not in put_call
    assert storage.exists(audio_key)
    assert storage.get_bytes(audio_key) == b"RIFFDATA"
    assert storage.list_keys("uploads/") == [audio_key]

    storage.delete(audio_key)
    assert not storage.exists(audio_key)


def test_create_storage_and_singleton_hook():
    mem_settings = Settings(storage_backend="auto", ncp_access_key="", ncp_secret_key="")
    assert isinstance(create_storage(mem_settings), InMemoryObjectStorage)

    forced_mem = Settings(storage_backend="memory", ncp_access_key="ak", ncp_secret_key="sk")
    assert isinstance(create_storage(forced_mem), InMemoryObjectStorage)

    ncp_settings = Settings(storage_backend="auto", ncp_access_key="ak", ncp_secret_key="sk")
    assert isinstance(create_storage(ncp_settings), NcpObjectStorage)

    bad_ncp = Settings(storage_backend="ncp", ncp_access_key="", ncp_secret_key="")
    with pytest.raises(ValueError):
        create_storage(bad_ncp)

    custom = InMemoryObjectStorage()
    set_storage(custom)
    try:
        assert get_storage() is custom
    finally:
        set_storage(None)
