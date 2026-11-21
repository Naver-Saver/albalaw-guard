"""프롬프트 템플릿. 파일로 분리해 AI 담당이 코드 수정 없이 다듬을 수 있게 한다."""

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache
def load(name: str) -> str:
    return (_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
