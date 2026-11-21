"""CLOVA Chatbot FAQ 판정 점검 스크립트 (BR-11 임계값 조정용). 실제 Chatbot을 호출한다 (질문당 1회).

사용법 (backend/ 디렉터리에서):
    python scripts/faq_probe.py [질문 파일]      # 기본: samples/faq_probe.json

질문 파일 형식: [{"q": "질문", "exp": ["기대하는 시나리오 이름", ...]}, ...]
  exp 가 비어 있으면 'FAQ에 없는 질문'(FAQ로 답하면 오답)이다.
리허설에서 쓸 질문을 같은 형식으로 추가해 돌리면 임계값(clova_chatbot.FAQ_MIN_SCORE)과
핵심어 확인(ask.faq_fits_question)이 괜찮은지 볼 수 있다.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import ask, clova_chatbot  # noqa: E402

DEFAULT_CASES = BACKEND_ROOT / "samples" / "faq_probe.json"
THRESHOLDS = (0.7, 0.75, 0.8, 0.85, 0.9)


async def run(cases: list[dict]) -> list[tuple[dict, clova_chatbot.ChatbotAnswer]]:
    return [(c, await clova_chatbot.ask(c["q"])) for c in cases]


def accepted(reply: clova_chatbot.ChatbotAnswer, q: str, threshold: float, with_guard: bool) -> bool:
    if reply.is_fallback or reply.score is None or reply.score < threshold:
        return False
    return ask.faq_fits_question(q, reply) if with_guard else True


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CASES
    cases = json.loads(path.read_text(encoding="utf-8"))
    results = asyncio.run(run(cases))
    expected_total = sum(1 for c, _ in results if c["exp"])

    print(f"질문 {len(results)}개 (FAQ에 있는 질문 {expected_total}개)")
    print(f"현재 기준: 점수 {clova_chatbot.FAQ_MIN_SCORE} 이상 + 핵심어 확인")
    print()
    for c, r in results:
        used = accepted(r, c["q"], clova_chatbot.FAQ_MIN_SCORE, True)
        if used:
            mark = "OK   " if r.scenario in c["exp"] else "WRONG"
        else:
            mark = "MISS " if c["exp"] else "ok   "
        score = "-" if r.score is None else f"{r.score:.3f}"
        print(f"{mark} {score:>5} {r.matching_type or '-':10} {r.scenario or '-'} <- {c['q']}")

    print("\n기준별 결과 (정답=FAQ가 맞게 답함, 오답=엉뚱한 FAQ가 답함)")
    for guard in (False, True):
        for t in THRESHOLDS:
            tp = sum(1 for c, r in results if accepted(r, c["q"], t, guard) and r.scenario in c["exp"])
            fp = sum(1 for c, r in results if accepted(r, c["q"], t, guard) and r.scenario not in c["exp"])
            label = "점수+핵심어" if guard else "점수만   "
            print(f"  {label} >= {t:.2f}: 정답 {tp}/{expected_total}, 오답 {fp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
