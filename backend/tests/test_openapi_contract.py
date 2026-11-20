"""SDD 계약 검사: 구현된 API는 모두 docs/spec/openapi.yaml에 정의되어 있어야 한다."""

from pathlib import Path

import yaml

from app.main import app

SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "spec" / "openapi.yaml"
SERVER_PREFIX = "/api"
METHODS = {"get", "post", "put", "patch", "delete"}


def _spec_operations() -> set[str]:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    return {
        f"{method.upper()} {SERVER_PREFIX}{path}"
        for path, item in spec["paths"].items()
        for method in item
        if method in METHODS
    }


def _implemented_operations() -> set[str]:
    impl = app.openapi()
    return {f"{method.upper()} {path}" for path, item in impl["paths"].items() for method in item}


def test_every_implemented_route_is_specified():
    missing = _implemented_operations() - _spec_operations()
    assert not missing, f"명세(openapi.yaml)에 없는 API가 구현되어 있습니다: {sorted(missing)}"


def test_spec_operations_have_spec_id():
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    no_id = [
        f"{m.upper()} {p}"
        for p, item in spec["paths"].items()
        for m, op in item.items()
        if m in METHODS and "x-spec-id" not in op
    ]
    assert not no_id, f"x-spec-id가 없는 operation: {no_id}"
