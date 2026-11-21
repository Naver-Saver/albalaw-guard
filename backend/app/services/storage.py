"""Object Storage 공통 모듈 (A·B·C 공용).

NCP Object Storage(S3 호환 boto3)와 로컬/테스트용 In-Memory 구현을 동일한 Protocol로 제공한다.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Protocol, runtime_checkable

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings

logger = logging.getLogger("app.storage")

_NOT_FOUND_CODES = frozenset({"NoSuchKey", "404", "NotFound"})


class StorageKeys:
    """Object Storage 버킷 내 객체 키 규칙."""

    LAW_DATA_DEFAULT = "law-data/manyask-worker.json"
    LAW_QNA = "law/qna_labor.json"
    LAW_RULES = "law/lifelaw_rules.json"
    LAW_FAQ = "law/lifelaw_faq.json"
    WAGE_MIN = "wage/min_wage.json"
    META_SYNC_LOG = "meta/sync_log.json"

    @staticmethod
    def _clean_ext(ext: str) -> str:
        return ext.lstrip(".").strip().lower()

    @classmethod
    def upload_recording(cls, job_id: str, ext: str, prefix: str = "uploads/") -> str:
        clean_prefix = prefix.strip("/")
        clean_ext = cls._clean_ext(ext)
        if clean_prefix:
            return f"{clean_prefix}/{job_id}.{clean_ext}"
        return f"{job_id}.{clean_ext}"

    @classmethod
    def upload_audio(cls, conv_id: str, ext: str) -> str:
        return f"uploads/audio/{conv_id}.{cls._clean_ext(ext)}"

    @staticmethod
    def speech_result(conv_id: str) -> str:
        return f"results/speech/{conv_id}.json"

    @staticmethod
    def report_result(result_id: str) -> str:
        return f"results/report/{result_id}.json"


@runtime_checkable
class ObjectStorage(Protocol):
    """A·B·C 모듈이 공통으로 의존하는 객체 스토리지 인터페이스."""

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """바이너리 데이터를 비공개로 업로드하고 저장 키를 반환한다."""

    def get_bytes(self, key: str) -> bytes | None:
        """객체 바이트를 조회한다. 존재하지 않으면 None을 반환한다."""

    def put_json(self, key: str, payload: dict[str, Any]) -> str:
        """JSON 직렬화 가능한 딕셔너리를 업로드하고 저장 키를 반환한다."""

    def get_json(self, key: str) -> dict[str, Any] | None:
        """JSON 객체를 파싱해 반환한다. 존재하지 않으면 None을 반환한다."""

    def exists(self, key: str) -> bool:
        """키가 스토리지에 존재하는지 확인한다."""

    def delete(self, key: str) -> None:
        """객체를 삭제한다. 이미 없어도 예외를 발생시키지 않는다."""

    def list_keys(self, prefix: str = "") -> list[str]:
        """지정한 접두사로 시작하는 객체 키 목록을 정렬해 반환한다."""


class InMemoryObjectStorage:
    """로컬 무키 개발 및 pytest 격리 실행용 스레드 안전 인메모리 스토리지."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._objects: dict[str, tuple[bytes, str]] = {}

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        with self._lock:
            self._objects[key] = (bytes(data), content_type)
        return key

    def get_bytes(self, key: str) -> bytes | None:
        with self._lock:
            entry = self._objects.get(key)
        return entry[0] if entry is not None else None

    def put_json(self, key: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self.upload_bytes(key, encoded, content_type="application/json; charset=utf-8")

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self.get_bytes(key)
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8"))

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._objects

    def delete(self, key: str) -> None:
        with self._lock:
            self._objects.pop(key, None)

    def list_keys(self, prefix: str = "") -> list[str]:
        with self._lock:
            return sorted(k for k in self._objects if k.startswith(prefix))


class NcpObjectStorage:
    """NCP Object Storage (S3 호환 boto3) 구현체."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        region_name: str,
        access_key: str,
        secret_key: str,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self._client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        # 개인정보 보호를 위해 절대 public-read ACL을 지정하지 않는다.
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def get_bytes(self, key: str) -> bytes | None:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _is_not_found_error(exc):
                return None
            logger.warning("object storage get failed: key=%s code=%s", key, _error_code(exc))
            raise
        return resp["Body"].read()

    def put_json(self, key: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self.upload_bytes(key, encoded, content_type="application/json; charset=utf-8")

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self.get_bytes(key)
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8"))

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if _is_not_found_error(exc):
                return False
            logger.warning("object storage head failed: key=%s code=%s", key, _error_code(exc))
            raise

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _is_not_found_error(exc):
                return
            logger.warning("object storage delete failed: key=%s code=%s", key, _error_code(exc))
            raise

    def list_keys(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        continuation_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            resp = self._client.list_objects_v2(**kwargs)
            for item in resp.get("Contents", []):
                key = item.get("Key")
                if isinstance(key, str):
                    keys.append(key)
            if not resp.get("IsTruncated"):
                break
            continuation_token = resp.get("NextContinuationToken")
            if not continuation_token:
                break
        return sorted(keys)


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _is_not_found_error(exc: ClientError) -> bool:
    code = _error_code(exc)
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in _NOT_FOUND_CODES or status == 404


def create_storage(settings: Settings) -> ObjectStorage:
    """설정에 따라 NCP Object Storage 또는 In-Memory 스토리지를 생성한다."""
    mode = settings.storage_backend.strip().lower()
    has_keys = bool(settings.ncp_access_key and settings.ncp_secret_key)

    if mode == "memory":
        return InMemoryObjectStorage()
    if mode == "ncp" and not has_keys:
        raise ValueError("STORAGE_BACKEND=ncp 사용 시 NCP_ACCESS_KEY/NCP_SECRET_KEY가 필요합니다.")
    if mode == "ncp" or (mode == "auto" and has_keys):
        return NcpObjectStorage(
            bucket=settings.object_storage_bucket,
            endpoint_url=settings.object_storage_endpoint,
            region_name=settings.object_storage_region,
            access_key=settings.ncp_access_key,
            secret_key=settings.ncp_secret_key,
        )
    return InMemoryObjectStorage()


_storage_lock = threading.Lock()
_storage_instance: ObjectStorage | None = None


def set_storage(storage: ObjectStorage | None) -> None:
    """테스트에서 스토리지 더블을 주입·초기화하기 위한 훅."""
    global _storage_instance
    with _storage_lock:
        _storage_instance = storage


def get_storage() -> ObjectStorage:
    """애플리케이션 공용 ObjectStorage 싱글턴을 반환한다."""
    global _storage_instance
    with _storage_lock:
        if _storage_instance is None:
            _storage_instance = create_storage(get_settings())
        return _storage_instance
