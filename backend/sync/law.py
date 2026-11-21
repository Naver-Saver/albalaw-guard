"""국가법령정보센터(open.law.go.kr) Open API → law-data/law-articles.json.

사용: python -m sync.law [--dry-run] [--save-raw] [--laws 근로기준법 최저임금법 ...]
- 법령명으로 검색(lawSearch.do) → 법령ID → 본문 조회(lawService.do) → 조문 단위로 정리.
- OC 아이디는 환경변수/ .env 의 LAW_GO_KR_OC 에서 읽는다 (로그·출력에 URL 전체를 남기지 않음).
- 파싱 구조는 samples/raw/law_go_kr/ 의 실제 응답 기준.
"""

import argparse
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from sync.common import DRY_RUN_DIR, RAW_DIR, now_kst_iso, read_env, write_json

BASE_URL = "https://www.law.go.kr/DRF/"
DEFAULT_LAWS = [
    "근로기준법",
    "근로기준법 시행령",
    "최저임금법",
    "최저임금법 시행령",
    "근로자퇴직급여 보장법",
]
OUTPUT_NAME = "law-articles.json"
REQUEST_INTERVAL = 0.4


def load_oc() -> str:
    oc = read_env("LAW_GO_KR_OC")
    if not oc:
        raise SystemExit("LAW_GO_KR_OC 가 설정되어 있지 않습니다 (backend/.env).")
    return oc


def _get(endpoint: str, oc: str, **params: str) -> bytes:
    last: Exception | None = None
    for _ in range(2):  # 실패 시 1회 재시도
        try:
            r = httpx.get(BASE_URL + endpoint, params={"OC": oc, "type": "XML", **params}, timeout=30)
            r.raise_for_status()
            time.sleep(REQUEST_INTERVAL)
            return r.content
        except httpx.HTTPError as e:
            last = e
            time.sleep(1)
    # 예외 메시지에는 URL(OC 포함)이 들어갈 수 있으므로 종류만 남긴다
    raise RuntimeError(f"법제처 API 호출 실패: {endpoint} ({type(last).__name__})")


def find_law_id(search_xml: bytes, law_name: str) -> str:
    """검색 결과에서 법령명이 정확히 일치하는 현행 법령의 법령ID를 고른다."""
    root = ET.fromstring(search_xml)
    code = root.findtext("resultCode")
    if code not in (None, "00"):
        raise RuntimeError(f"법제처 검색 오류: {code} {root.findtext('resultMsg')}")
    for law in root.findall("law"):
        if (law.findtext("법령명한글") or "").strip() == law_name:
            law_id = (law.findtext("법령ID") or "").strip()
            if law_id:
                return law_id
    raise LookupError(f"법령을 찾을 수 없습니다: {law_name}")


def _text(el: ET.Element | None, tag: str) -> str:
    return ((el.findtext(tag) if el is not None else "") or "").strip()


def _clean(s: str) -> str:
    return re.sub(r"[ \t\u3000]+", " ", s).strip()


def article_text(article: ET.Element) -> str:
    """조문내용 + 항 + 호를 줄바꿈으로 이어 붙인 본문."""
    lines = [_clean(_text(article, "조문내용"))]
    for hang in article.findall("항"):
        lines.append(_clean(_text(hang, "항내용")))
        for ho in hang.findall("호"):
            lines.append("  " + _clean(_text(ho, "호내용")))
    return "\n".join(line for line in lines if line.strip())


def article_label(no: str, branch: str) -> str:
    return f"제{no}조" + (f"의{branch}" if branch else "")


def parse_law(xml_bytes: bytes) -> tuple[dict, list[dict]]:
    """법령 본문 XML → (법령 정보, 조문 목록). 장(전문)·삭제 조문은 제외하되 장 제목은 chapter에 기록."""
    root = ET.fromstring(xml_bytes)
    info = root.find("기본정보")
    law_id = _text(info, "법령ID")
    law_name = _text(info, "법령명_한글")
    effective = _text(info, "시행일자")
    if not (law_id and law_name):
        raise ValueError("법령 기본정보를 찾을 수 없습니다.")

    articles: list[dict] = []
    chapter = ""
    for a in root.findall("./조문/조문단위"):
        kind = _text(a, "조문여부")
        if kind == "전문":
            chapter = _clean(_text(a, "조문내용"))
            continue
        if kind != "조문":
            continue
        no, branch = _text(a, "조문번호"), _text(a, "조문가지번호")
        title = _text(a, "조문제목")
        text = article_text(a)
        if re.match(r"^제\d+조(의\d+)?\s*삭제", text):
            continue  # 삭제된 조문
        label = article_label(no, branch)
        articles.append(
            {
                "id": f"law-{law_id}-{no}" + (f"-{branch}" if branch else ""),
                "source": "LAW_API",
                "lawId": law_id,
                "lawName": law_name,
                "chapter": chapter,
                "articleNo": label,
                "title": title,
                "text": text,
                "effectiveDate": _text(a, "조문시행일자") or effective,
                "sourceUrl": f"https://www.law.go.kr/법령/{law_name}/{label}",
            }
        )
    return {"lawId": law_id, "lawName": law_name, "effectiveDate": effective}, articles


def collect(law_names: list[str], oc: str, save_raw: bool) -> dict:
    items: list[dict] = []
    laws: list[dict] = []
    for name in law_names:
        search_xml = _get("lawSearch.do", oc, target="law", query=name)
        law_id = find_law_id(search_xml, name)
        body = _get("lawService.do", oc, target="law", ID=law_id)
        if save_raw:
            RAW_DIR.joinpath("law_go_kr").mkdir(parents=True, exist_ok=True)
            (RAW_DIR / "law_go_kr" / f"service_{name.replace(' ', '_')}_ID{law_id}.xml").write_bytes(body)
        info, articles = parse_law(body)
        laws.append({**info, "articleCount": len(articles)})
        items.extend(articles)
        print(f"{name}: {len(articles)}개 조문 (시행일자 {info['effectiveDate']})")
    return {"source": "LAW_API", "syncedAt": now_kst_iso(), "laws": laws, "items": items}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="국가법령정보센터 조문 수집")
    parser.add_argument("--laws", nargs="+", default=DEFAULT_LAWS)
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 backend/data/law-data/ 에 저장")
    parser.add_argument("--save-raw", action="store_true", help="원본 XML을 samples/raw/law_go_kr/ 에 저장")
    args = parser.parse_args(argv)
    if not args.dry_run:
        raise SystemExit(
            "업로드는 아직 연결되지 않았습니다 (C의 storage 모듈 대기). --dry-run 으로 실행하세요."
        )

    payload = collect(args.laws, load_oc(), args.save_raw)
    out: Path = DRY_RUN_DIR / OUTPUT_NAME
    write_json(out, payload)
    print(f"총 {len(payload['items'])}건 저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
