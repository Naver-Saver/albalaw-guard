"""외부 API 호출 공통 처리: 타임아웃, 1회 재시도(타임아웃·5xx). 05-ai-pipeline '공통 실패 처리'."""

import logging

import httpx

logger = logging.getLogger("app.http")

# 테스트에서 httpx.MockTransport를 꽂기 위한 훅
_transport: httpx.AsyncBaseTransport | None = None


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    global _transport
    _transport = transport


async def post_with_retry(
    service: str, url: str, *, timeout: float, retries: int = 1, **kwargs
) -> httpx.Response:
    """성공(2xx)·클라이언트 오류(4xx) 응답은 그대로 반환하고, 타임아웃·5xx만 재시도한다.

    마지막 시도까지 실패하면 httpx.HTTPError 를 던진다. 키·본문은 로그에 남기지 않는다.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=_transport) as client:
                res = await client.post(url, **kwargs)
            if res.status_code < 500:
                return res
            logger.warning("%s upstream %s (attempt %d)", service, res.status_code, attempt + 1)
            last_exc = httpx.HTTPStatusError(
                f"{service} {res.status_code}", request=res.request, response=res
            )
        except httpx.TimeoutException as e:
            logger.warning("%s timeout (attempt %d)", service, attempt + 1)
            last_exc = e
    assert last_exc is not None
    raise last_exc
