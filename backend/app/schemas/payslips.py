from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.contracts import CheckItem, Source

Lang = Literal["ko", "en", "vi", "zh-CN"]


class PayslipLine(BaseModel):
    """명세서의 한 줄 (항목 이름과 금액)."""

    name: str = Field(
        ..., min_length=1, max_length=50, description="항목 이름 (예: 기본급, 주휴수당, 국민연금)"
    )
    amount: int = Field(..., ge=0, le=1_000_000_000, description="금액(원)")


class PayslipReviewRequest(BaseModel):
    """사용자가 확인·수정한 급여명세서 값. 이름·지급일은 있는지만 보고 저장하지 않는다."""

    employee_name: str | None = Field(None, max_length=50, description="근로자 식별 정보 (있는지만 확인)")
    pay_date: str | None = Field(None, max_length=30, description="임금지급일")
    items: list[PayslipLine] = Field(default_factory=list, max_length=30, description="지급 항목")
    deductions: list[PayslipLine] = Field(default_factory=list, max_length=30, description="공제 항목")
    total_pay: int | None = Field(None, ge=0, le=1_000_000_000, description="임금 총액")
    net_pay: int | None = Field(None, ge=0, le=1_000_000_000, description="실지급액")
    calculation_method: str | None = Field(None, max_length=300, description="항목별 계산방법 (시간 수 등)")
    hourly_wage: int | None = Field(None, gt=0, le=10_000_000, description="시급(원, 알면 입력)")
    weekly_hours: float | None = Field(None, gt=0, le=168, description="1주 소정근로시간(알면 입력)")
    year: int = Field(default_factory=lambda: date.today().year, description="최저임금 적용 연도")
    lang: Lang = "ko"


class PayslipMismatch(BaseModel):
    field: Literal["totalPay", "netPay"]
    expected: int
    actual: int
    difference: int


class PayslipTotals(BaseModel):
    """코드로 검산한 숫자 (LLM이 아니라 calc.check_payslip_totals 결과)."""

    items_sum: int
    deductions_sum: int
    total_pay: int | None
    net_pay: int | None
    expected_net_pay: int
    total_matches: bool | None
    net_matches: bool | None
    mismatches: list[PayslipMismatch]


class MissingField(BaseModel):
    item: str
    field_key: str
    source_ids: list[str]
    conditional: bool = Field(description="상황에 따라 없어도 되는 항목이면 true (확인 후보)")


class PayslipWage(BaseModel):
    year: int
    minimum_wage: int
    hourly_wage: int
    is_below_minimum: bool
    shortfall_per_hour: int
    weekly_holiday_eligible: bool
    weekly_holiday_hours: float
    weekly_holiday_pay: int


class PayslipReviewResult(BaseModel):
    totals: PayslipTotals
    wage: PayslipWage | None = None
    missing: list[MissingField]
    items: list[CheckItem]
    sources: list[Source]
    disclaimer: str
