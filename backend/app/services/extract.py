"""OCR 텍스트에서 근로조건 항목을 규칙 기반으로 추출한다 — BR-02.

- 문서에 직접 적힌 값: confidence = high
- 다른 값으로 계산한 값: confidence = low (사용자 확인 화면에서 강조)
- 못 찾은 값: value = None, confidence = low
"""

import re
from dataclasses import dataclass

from app.schemas.contracts import ExtractedField, ExtractedFields, PayslipExtracted, PayslipLineExtracted

DAYS = "월화수목금토일"
_DAY = f"[{DAYS}]"
_SEP = r"\s*[~\-–—]\s*"

MIN_HOURLY, MAX_HOURLY = 1_000, 100_000

# 표준근로계약서의 "시간(일, 월)급 : 10,320원(해당사항에 ○표)" 처럼 시간·일·월급을 함께 적는 표기는
# 금액이 시급 범위일 때만 시급으로 보고 confidence=low 로 둔다 (사용자 확인 필요).
_AMBIGUOUS_WAGE = r"시간\s*[(（][^)）]{0,12}[)）]\s*급"
_RE_WAGE = re.compile(
    rf"(?P<kw>시\s*급|시간\s*급|시간당\s*(?:임금|급여)?|{_AMBIGUOUS_WAGE})"
    r"\s*(?:\(\s*원\s*\))?\s*[:：]?\s*(?:금\s*)?"
    r"(?:(?P<man>\d+)\s*만\s*(?P<rest>\d[\d,]*)?|(?P<num>\d[\d,]*))\s*원?"
)
_RE_YEAR = re.compile(r"(?P<y>20\d{2})\s*[년.\-/]")
_YEAR_KEYWORDS = ("근로계약기간", "계약기간", "근로개시", "계약 기간")
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
    confidence: str = "high"


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
                ambiguous = "(" in m.group("kw") or "（" in m.group("kw")
                return _Found(value, m.group(0).strip(), "low" if ambiguous else "high")
    return None


def find_year(lines: list[str]) -> _Found | None:
    """적용 연도: 근로계약기간 시작 연도(high) → 그 밖의 날짜 연도(low, 작성일 등)."""

    def pick(line: str) -> int | None:
        m = _RE_YEAR.search(line)
        return int(m.group("y")) if m and 2000 <= int(m.group("y")) <= 2100 else None

    for line in lines:
        if any(k in line.replace(" ", "") for k in _YEAR_KEYWORDS):
            year = pick(line)
            if year:
                return _Found(year, line.strip())
    for line in lines:
        year = pick(line)
        if year:
            return _Found(year, line.strip(), "low")
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


def _field(found: _Found | None, confidence: str | None = None) -> ExtractedField:
    if found is None:
        return ExtractedField()
    return ExtractedField(
        value=found.value, confidence=confidence or found.confidence, source_text=found.source
    )


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
        year=_field(find_year(lines)),
    )


# ---- 급여명세서 (doc_type=payslip) ----

_AMOUNT = r"\d{1,3}(?:,\d{3})+|\d{4,}"
_RE_PAY_PAIR = re.compile(
    rf"(?P<name>[가-힣A-Za-z][가-힣A-Za-z()·ㆍ\s]{{0,18}}?)\s*[:：]?\s*(?P<amt>{_AMOUNT})\s*원?"
)
_DEDUCTION_NAMES = (
    "국민연금",
    "건강보험",
    "장기요양",
    "고용보험",
    "산재보험",
    "소득세",
    "지방소득세",
    "주민세",
    "공제",
    "가불",
)
_TOTAL_PAY = ("지급총액", "지급합계", "임금총액", "총지급액", "급여총액", "지급액계", "총급여")
_TOTAL_DEDUCTION = ("공제총액", "공제합계", "공제액계", "총공제")
_NET_PAY = ("실지급액", "차인지급액", "실수령액", "실수령", "차감지급액", "실지급")
_RE_PAY_DATE = re.compile(r"(?:임금\s*)?지급\s*일(?:자)?\s*[:：]?\s*(?P<v>[0-9][0-9.\-/년월일\s]{3,20})")
_RE_NAME = re.compile(r"(?:성\s*명|이\s*름|근로자)\s*[:：]\s*(?P<v>[가-힣A-Za-z]{2,20})")
_RE_METHOD = re.compile(r"(?:계산\s*방법|산출\s*(?:방법|내역|근거))\s*[:：]?\s*(?P<v>.+)")


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", s)


def extract_payslip(lines: list[str]) -> PayslipExtracted:
    """급여명세서 OCR 줄에서 지급·공제 항목과 합계를 읽는다.
    한 줄에 '항목 금액' 쌍이 여러 개(지급|공제 2단 표) 있어도 각각 읽는다."""
    lines = [ln.strip() for ln in lines if ln and ln.strip()]
    out = PayslipExtracted()
    seen: set[tuple[str, int]] = set()
    for line in lines:
        if out.pay_date is None and (m := _RE_PAY_DATE.search(line)):
            out.pay_date = m.group("v").strip()
        if out.employee_name is None and (m := _RE_NAME.search(line)):
            out.employee_name = m.group("v")
        if out.calculation_method is None and (m := _RE_METHOD.search(line)):
            out.calculation_method = m.group("v").strip()[:300]
        if _RE_PAY_DATE.search(line):
            continue  # 날짜 줄의 숫자를 금액으로 읽지 않는다
        for m in _RE_PAY_PAIR.finditer(line):
            name = _compact(m.group("name")).strip("()")
            amount = int(m.group("amt").replace(",", ""))
            if len(name) < 2 or (name, amount) in seen:
                continue
            seen.add((name, amount))
            src = m.group(0).strip()
            if any(k in name for k in _TOTAL_PAY):
                out.total_pay = ExtractedField(value=amount, confidence="high", source_text=src)
            elif any(k in name for k in _NET_PAY):
                out.net_pay = ExtractedField(value=amount, confidence="high", source_text=src)
            elif any(k in name for k in _TOTAL_DEDUCTION):
                continue  # 공제 합계는 항목 합으로 검산하므로 따로 받지 않는다
            elif any(k in name for k in _DEDUCTION_NAMES):
                out.deductions.append(PayslipLineExtracted(name=name, amount=amount, source_text=src))
            elif not any(k in name for k in ("시급", "시간", "일수", "연도", "년", "월", "일")):
                out.items.append(PayslipLineExtracted(name=name, amount=amount, source_text=src))
    return out
