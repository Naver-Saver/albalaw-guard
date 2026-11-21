"""app/api/routes/ 의 모든 라우터가 main 앱에 등록됐는지 검사 (#28).

라우터 파일만 추가하고 main.py 등록을 빠뜨리면 테스트 전용 앱으로는 통과해도 운영에서 404가 난다.
"""

import importlib
import pkgutil

from app.api import routes
from app.main import app


def _main_paths() -> set[tuple[str, str]]:
    return {(m, r.path) for r in app.routes for m in getattr(r, "methods", set()) - {"HEAD", "OPTIONS"}}


def test_every_route_module_is_registered_on_main_app():
    registered = _main_paths()
    missing = []
    for info in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f"{routes.__name__}.{info.name}")
        router = getattr(module, "router", None)
        if router is None:
            continue
        for r in router.routes:
            for m in r.methods - {"HEAD", "OPTIONS"}:
                if (m, f"/api{r.path}") not in registered:
                    missing.append(f"{info.name}: {m} /api{r.path}")
    assert not missing, "main.py 에 등록되지 않은 라우트: " + ", ".join(missing)
