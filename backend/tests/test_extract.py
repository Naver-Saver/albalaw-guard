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


STANDARD_FORM = """표준근로계약서(단시간근로자)
1. 근로계약기간 : 2026년 3월 2일부터 2026년 12월 31일까지
4. 근로일 및 근로일별 근로시간
- 근로일 : 월, 수, 금
- 근로시간 : 10시 00분부터 16시 00분까지
- 휴게시간 : 12시 00분부터 12시 30분까지
5. 임금
- 시간(일, 월)급: 10,320원(해당사항에 ◯표)
- 임금지급일 : 매월 10일(휴일의 경우는 전일 지급)
2026년 3월 2일""".splitlines()


def test_standard_form_wage_and_year_are_filled():
    """#65: 표준근로계약서 서식의 시급·적용 연도가 입력값으로 채워진다."""
    f = extract_fields(STANDARD_FORM)
    assert f.hourly_wage.value == 10_320 and f.hourly_wage.confidence == "low"  # 시간·일·월급 겸용 표기
    assert "10,320" in f.hourly_wage.source_text
    assert f.year.value == 2026 and f.year.confidence == "high"
    assert "근로계약기간" in f.year.source_text
    assert f.work_days.value == ["월", "수", "금"]
    assert f.break_minutes.value == 30
    assert f.weekly_hours.value == 16.5


def test_monthly_salary_is_not_taken_as_hourly_wage():
    f = extract_fields(["임금 - 시간(일, 월)급 : 2,500,000원", "작성일 2027. 1. 2."])
    assert f.hourly_wage.value is None
    assert f.year.value == 2027 and f.year.confidence == "low"


def test_wage_label_variants():
    assert extract_fields(["시 급(원): 10,700"]).hourly_wage.value == 10_700
    assert extract_fields(["임금 : 시간당 1만 320원"]).hourly_wage.value == 10_320
    assert extract_fields(["시급 10,320원"]).hourly_wage.confidence == "high"


def test_payslip_two_column_lines():
    from app.services.extract import extract_payslip

    p = extract_payslip(
        [
            "2026년 4월분 급여명세서",
            "성명 : 홍길동   임금지급일 : 2026. 5. 10.",
            "기본급 990,720  국민연금 44,580",
            "주휴수당 165,120  건강보험 35,120",
            "연장근로수당 0  고용보험 10,400",
            "지급총액 1,155,840  공제총액 90,100",
            "실지급액 1,065,740",
            "계산방법: 시급 10,320원 × 96시간",
        ]
    )
    assert p.employee_name == "홍길동" and p.pay_date.startswith("2026")
    assert [(i.name, i.amount) for i in p.items] == [("기본급", 990_720), ("주휴수당", 165_120)]
    assert [d.name for d in p.deductions] == ["국민연금", "건강보험", "고용보험"]
    assert p.total_pay.value == 1_155_840 and p.net_pay.value == 1_065_740
    assert p.calculation_method.startswith("시급 10,320원")
