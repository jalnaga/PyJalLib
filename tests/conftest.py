# -*- coding: utf-8 -*-
"""pytest conftest.py - 공통 테스트 설정.

pymxs를 포함한 3ds Max 전용 모듈들을 mock 처리하여
콘솔 환경(Type A)에서도 테스트가 실행될 수 있도록 한다.
"""

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# DCC 전용 스크립트 자동 제외 (collect_ignore)
#
# 이전에는 `pyproject.toml`의 `addopts`에 `--ignore=...`를 **손으로 26개 나열**했다.
# 그 목록은 신규 Type C 파일마다 잠복하는 결함원이었다 - 2026-09-06 SkinTransfer와
# 2026-09-15 EnvelopeFix에서 **두 번** 재발했고(규약은 문서에 있었다), 16차 복기 세션 3
# 시점 실측에서 **stale 9건 + 누락 5건**이 동시에 있었다.
#
# 목록을 사람이 관리하는 한 같은 결함이 계속 난다. 그래서 판정을 **파일 내용**으로
# 바꾼다 - DCC 런타임을 import하면 콘솔 수집 대상이 아니다.
# `rules/testing.md`의 유형 판별("DCC API import 없음 -> Type A")과 같은 축이다.
#
# 축에 무엇을 넣는지는 실측으로 정했다:
#   - `pymxs` / `unreal`: rules가 지목하는 DCC API.
#   - `qtmax`: 3ds Max의 Qt 브리지. 호스트 안에서만 존재한다.
#   - **PySide2/PySide6는 넣지 않는다.** 콘솔 venv에 실재하고 Type A 4건
#     (`test_fuzzy_filter_proxy` · `test_fuzzy_search_combo_box` · `test_progress_window` ·
#     `test_tool_state`)이 정상 사용 중이다 - 넣으면 그 4건을 과다 제외한다.
#
# 함수 안의 지연 import도 센다. 지연이든 아니든 **그 스크립트는 DCC 없이는 완주하지
# 못하기 때문**이다(`test_ui_fuzzy_search_combo_box`가 정확히 그 형태다 - 모듈 수준은
# PySide뿐이고 `qtmax`는 함수 안에 있다).
# ---------------------------------------------------------------------------

_DCC_IMPORT_PATTERN = re.compile(
    r"^\s*(?:import|from)\s+(?:pymxs|unreal|qtmax)\b", re.M
)
_TESTS_DIR = Path(__file__).parent


def _is_dcc_only(inPath: Path) -> bool:
    """DCC 런타임을 import하는 스크립트인지 판정한다(지연 import 포함).

    Args:
        inPath: 검사할 `.py` 파일 경로

    Returns:
        `pymxs` / `unreal` / `qtmax` 중 하나라도 import하면 True
    """
    try:
        text = inPath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return _DCC_IMPORT_PATTERN.search(text) is not None


def _collect_dcc_only_scripts() -> list[str]:
    """`tests/` 아래 DCC 전용 스크립트의 상대경로 목록을 만든다.

    Returns:
        conftest 기준 상대경로 문자열 목록(pytest `collect_ignore` 형식)
    """
    found = [
        p.relative_to(_TESTS_DIR).as_posix()
        for p in sorted(_TESTS_DIR.rglob("*.py"))
        if p.name != "conftest.py" and _is_dcc_only(p)
    ]
    # 러너는 DCC를 import하지 않지만 테스트가 아니다 - 이름 규칙 밖이라 수집되지 않으나
    # 명시해 두어 의도를 남긴다.
    found.append("run_max_tests.py")
    return found


collect_ignore = _collect_dcc_only_scripts()

# 3ds Max 전용 모듈을 sys.modules에 mock 등록
# pyjallib.max.__init__ 로드 시 pymxs import가 시도되므로
# 반드시 실제 import 전에 등록해야 한다.
_MAX_MOCK_MODULES = [
    "pymxs",
    "pymxs.runtime",
]

for _modName in _MAX_MOCK_MODULES:
    if _modName not in sys.modules:
        sys.modules[_modName] = MagicMock()

# toolState 모듈이 로드되면 _HAS_PYMXS를 False로 강제 설정한다.
# pymxs가 mock으로 등록되어 import가 성공하므로 _HAS_PYMXS=True가 되는 문제를 방지.
import importlib
import pyjallib.max.ui.toolState as _toolStateModule
_toolStateModule._HAS_PYMXS = False
