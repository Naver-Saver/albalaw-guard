"""OCR 텍스트에서 근로조건 항목을 규칙 기반으로 추출한다 — BR-02.

- 문서에 직접 적힌 값: confidence = high
- 다른 값으로 계산한 값: confidence = low (사용자 확인 화면에서 강조)
- 못 찾은 값: value = None, confidence = low
"""

import re
from dataclasses import dataclass

from app.schemas.contracts import ExtractedField, ExtractedFields

DAYS = "월화수목금토일"
_DAY = f"[{DAYS}]"
_SEP = r"\s*[~\-–—]\s*"

MIN_HOURLY, MAX_HOURLY = 1_000, 100_000

_RE_WAGE = re.compile(
    r"(?:시급|시간급|시간당\s*(?:임금|급여)?)\s*[:：]?\s*(?:금\s*)?"
    r"(?:(?P<man>\d+)\s*만\s*(?P<rest>\d[\d,]*)?|(?P<num>\d[\d,]*))\s*원?"
)
_RE_WEEKLY = re.compile(
    r"(?:1\s*)?주\s*(?:당\s*)?(?:소정\s*)?(?:근로|근무)?\s*(?:시간)?\s*[:：]?\s*(?P<h>\d+(?:\.\d+)?)\s*시간"
)
_RE_DAY_RANGE = re.compile(rf"(?P<a>{_DAY})\s*(?:요일)?{_SEP}(?P<b>{_DAY})\s*(?:요일)?")
_RE_DAY_LIST = re.compile(rf"{_DAY}(?:요일)?(?:\s*[,·/]\s*{_DAY}(?:요일)?)+")
_RE_DAY_COUNT = re.compile(r"주\s*(?P<n>[1-7])\s*일")
_TIME = r"(?P<{p}h>\d{{1,2}})\s*(?::|시)\s*(?P<{p}m>\d{{2}})?\s*분?"
_RE_TIME_RANGE = re.compile(_TIME.format(p="s") + r"\s*(?:~|-|–|부터)\s*" + _TIME.format(p="e"))
_RE_BREAK_MIN = re.compile(r"(?P<n>\d+)\s*분")
_RE_BREAK_HOUR = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*시간")

_WORK_KEYWORDS = ("근무", "근로", "업무", "출근")


@dataclass
class _Found:
    value: object
    source: str


def _clean_number(s: str) -> int:
    return int(s.replace(",", ""))


def find_hourly_wage(lines: list[str]) -> _Found | None:
    for line in lines:
        for m in _RE_WAGE.finditer(line):
            if m.group("man"):
                value = int(m.group("man")) * 10_000 + (
                    _clean_number(m.group("rest")) if m.group("rest") else 0
                )
            else:
                value = _clean_number(m.group("num"))
            if MIN_HOURLY <= value <= MAX_HOURLY:
                return _Found(value, m.group(0).strip())
    return None


def find_weekly_hours(lines: list[str]) -> _Found | None:
    for line in lines:
        if "휴게" in line:
            continue
        m = _RE_WEEKLY.search(line)
        if m:
            hours = float(m.group("h"))
            if 0 < hours <= 68:
                return _Found(int(hours) if hours.is_integer() else hours, m.group(0).strip())
    return None


def _day_range(a: str, b: str) -> list[str]:
    i, j = DAYS.index(a), DAYS.index(b)
    if i <= j:
        return list(DAYS[i : j + 1])
    return list(DAYS[i:] + DAYS[: j + 1])  # 토~월 처럼 주말을 넘는 범위


def _before_break(line: str) -> str:
    """'휴게' 앞부분만 남긴다. 근로시간과 휴게시간이 한 줄에 함께 적힌 경우를 처리."""
    return line.split("휴게", 1)[0].strip()


def find_work_days(lines: list[str]) -> tuple[_Found | None, int | None, str | None]:
    """(요일 목록, 주 근무일 수, 근거 문구). 요일을 모르면 '주 N일'로 일수만 반환."""
    ordered = sorted(lines, key=lambda ln: not any(k in ln for k in (*_WORK_KEYWORDS, "요일")))
    for line in ordered:
        line = _before_break(line)
        if not line:
            continue
        m = _RE_DAY_RANGE.search(line)
        if m:
            days = _day_range(m.group("a"), m.group("b"))
            return _Found(days, m.group(0).strip()), len(days), m.group(0).strip()
        m = _RE_DAY_LIST.search(line)
        if m:
            days = [d for d in DAYS if d in m.group(0)]
            return _Found(days, m.group(0).strip()), len(days), m.group(0).strip()
    for line in lines:
        m = _RE_DAY_COUNT.search(line)
        if m:
            return None, int(m.group("n")), m.group(0).strip()
    return None, None, None


def _minutes(m: re.Match, p: str) -> int:
    return int(m.group(f"{p}h")) * 60 + int(m.group(f"{p}m") or 0)


def _range_minutes(m: re.Match) -> int:
    start, end = _minutes(m, "s"), _minutes(m, "e")
    if end <= start:
        end += 24 * 60  # 자정을 넘는 근무
    return end - start


def find_daily_minutes(lines: list[str]) -> _Found | None:
    ordered = sorted(lines, key=lambda ln: not any(k in ln for k in _WORK_KEYWORDS))
    for line in ordered:
        line = _before_break(line)
        if not line:
            continue
        m = _RE_TIME_RANGE.search(line)
        if m:
            minutes = _range_minutes(m)
            if 0 < minutes <= 16 * 60:
                return _Found(minutes, m.group(0).strip())
    return None


def find_break_minutes(lines: list[str]) -> _Found | None:
    for line in lines:
        if "휴게" not in line:
            continue
        tail = line[line.index("휴게") :]
        m = _RE_TIME_RANGE.search(tail)
        if m:
            return _Found(_range_minutes(m), m.group(0).strip())
        m = _RE_BREAK_MIN.search(tail)
        if m:
            return _Found(int(m.group("n")), m.group(0).strip())
        m = _RE_BREAK_HOUR.search(tail)
        if m:
            return _Found(round(float(m.group("n")) * 60), m.group(0).strip())
        if "없음" in tail:
            return _Found(0, tail.strip())
    return None


def _field(found: _Found | None, confidence: str = "high") -> ExtractedField:
    if found is None:
        return ExtractedField()
    return ExtractedField(value=found.value, confidence=confidence, source_text=found.source)


def extract_fields(lines: list[str]) -> ExtractedFields:
    lines = [ln.strip() for ln in lines if ln and ln.strip()]
    wage = find_hourly_wage(lines)
    days, day_count, day_source = find_work_days(lines)
    daily = find_daily_minutes(lines)
    brk = find_break_minutes(lines)
    weekly = find_weekly_hours(lines)

    weekly_field = _field(weekly)
    if weekly is None and day_count and daily:
        work = daily.value - (brk.value if brk else 0)
        if work > 0:
            hours = round(day_count * work / 60, 2)
            hours = int(hours) if float(hours).is_integer() else hours
            source = f"{day_source} / {daily.source}" + (f" / 휴게 {brk.source}" if brk else "")
            weekly_field = ExtractedField(value=hours, confidence="low", source_text=source)

    return ExtractedFields(
        hourly_wage=_field(wage),
        weekly_hours=weekly_field,
        work_days=_field(days),
        break_minutes=_field(brk),
    )
