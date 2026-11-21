from app.services.extract import extract_fields

CONTRACT = """표준근로계약서(단시간근로자)
1. 근로계약기간: 2026년 3월 2일부터
2. 근무장소: 카페 OOO
4. 근로일 및 근로일별 근로시간
근무요일: 월~금
근로시간: 10:00 ~ 14:30
휴게시간: 30분
5. 임금
시급: 10,000원
""".splitlines()


def test_standard_contract_computed_weekly_hours():
    f = extract_fields(CONTRACT)
    assert f.hourly_wage.value == 10_000 and f.hourly_wage.confidence == "high"
    assert f.work_days.value == ["월", "화", "수", "목", "금"]
    assert f.break_minutes.value == 30
    # 5일 × (4시간30분 − 30분) = 20시간, 계산값이라 low
    assert f.weekly_hours.value == 20 and f.weekly_hours.confidence == "low"


def test_explicit_weekly_hours_preferred():
    f = extract_fields(["1주 소정근로시간: 15시간", "시간급 1만 320원", "근무일 토, 일"])
    assert f.weekly_hours.value == 15 and f.weekly_hours.confidence == "high"
    assert f.hourly_wage.value == 10_320
    assert f.work_days.value == ["토", "일"]


def test_korean_hour_notation_and_overnight():
    f = extract_fields(["근무 요일 금요일~일요일", "근무시간 22시 ~ 6시", "휴게 시간 1시간", "시급 12,000원"])
    assert f.work_days.value == ["금", "토", "일"]
    # 3일 × (8시간 − 1시간) = 21시간
    assert f.weekly_hours.value == 21
    assert f.break_minutes.value == 60


def test_break_time_range():
    f = extract_fields(["근로시간 09:00~18:00", "휴게 12:00~13:00", "주 5일 근무"])
    assert f.break_minutes.value == 60
    assert f.weekly_hours.value == 40


def test_missing_values_are_null_low():
    f = extract_fields(["근로계약서", "성명 홍길동"])
    for field in (f.hourly_wage, f.weekly_hours, f.work_days, f.break_minutes):
        assert field.value is None and field.confidence == "low"


def test_ignores_out_of_range_wage():
    f = extract_fields(["시급 계산 예시 300원", "시급 9,860원"])
    assert f.hourly_wage.value == 9_860


def test_break_on_same_line_as_work_hours():
    f = extract_fields(["근로일: 월~금", "근로시간: 18:00 ~ 22:00 (휴게시간 30분)", "임금: 시간급 10,000원"])
    assert f.break_minutes.value == 30
    # 5일 × (4시간 − 30분) = 17.5시간
    assert f.weekly_hours.value == 17.5 and f.weekly_hours.confidence == "low"


def test_break_only_line_is_not_work_hours():
    f = extract_fields(["근로시간 09:00~18:00", "휴게 12:00~13:00", "주 5일 근무"])
    assert f.break_minutes.value == 60
    assert f.weekly_hours.value == 40
