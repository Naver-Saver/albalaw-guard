"""필수 항목 누락 후보 (파트 A). 각 항목에는 근거 source id 를 매핑해 둔다 — 근거 없는 항목은 추가하지 않는다.

fieldKey 는 API 명세(snake_case)의 추출 필드 이름이다. 값이 None/빈 문자열/빈 목록이면 '누락 후보'로 본다
(0 은 값이 있는 것으로 본다. 예: break_minutes=0).
이 결과는 확인이 필요한 후보일 뿐 위반 판단이 아니다.
"""

# 근거 id 는 law-data/law-articles.json 의 id (tests/test_checklist.py 가 존재 여부를 검사)
_ART17 = "law-001872-17"  # 근로기준법 제17조 근로조건의 명시
_ENF8 = "law-003058-8"  # 근로기준법 시행령 제8조 명시하여야 할 근로조건
_ENF27_2 = "law-003058-27-2"  # 근로기준법 시행령 제27조의2 임금명세서의 기재사항

# (항목 이름, fieldKey, 근거 id 목록, 조건부 여부)
CHECKLISTS: dict[str, list[tuple[str, str, list[str], bool]]] = {
    "CONTRACT": [
        ("임금(금액)", "hourly_wage", [_ART17], False),
        ("임금 지급방법", "wage_payment_method", [_ART17], False),
        ("임금 지급일", "wage_payment_date", ["law-001872-43"], False),
        ("소정근로시간", "weekly_hours", [_ART17], False),
        ("휴게시간", "break_minutes", ["law-001872-54", _ENF8], False),
        ("주휴일", "weekly_holiday", [_ART17], False),
        ("연차 유급휴가", "annual_leave", [_ART17], False),
        ("근무 장소", "work_place", [_ENF8], False),
        ("업무 내용", "job_description", [_ENF8], False),
    ],
    "PAYSLIP": [
        ("성명 등 근로자 식별 정보", "employee_name", [_ENF27_2], False),
        ("임금지급일", "pay_date", [_ENF27_2], False),
        ("임금 총액", "total_pay", [_ENF27_2], False),
        ("항목별 금액", "items", [_ENF27_2], False),
        ("항목별 계산방법", "calculation_method", [_ENF27_2], True),  # 금액이 근무시간 등에 따라 달라질 때
        ("공제 내역", "deductions", [_ENF27_2], True),  # 공제가 있을 때
    ],
}


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list | tuple | set | dict):
        return len(value) == 0
    return False


def find_missing(doc_type: str, fields: dict) -> list[dict]:
    """doc_type: "CONTRACT" | "PAYSLIP". 반환: [{"item", "fieldKey", "sourceIds", "conditional"}]
    conditional=True 는 상황에 따라 없어도 되는 항목(예: 공제가 없는 명세서)이라 CHECK_NEEDED 후보로만 쓴다.
    """
    if doc_type not in CHECKLISTS:
        raise ValueError(f"지원하지 않는 문서 유형입니다: {doc_type}")
    fields = fields or {}
    return [
        {"item": item, "fieldKey": key, "sourceIds": list(ids), "conditional": conditional}
        for item, key, ids, conditional in CHECKLISTS[doc_type]
        if _is_empty(fields.get(key))
    ]
