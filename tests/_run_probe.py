#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""프로브 전용 러너 - `tests/max/` 아래의 스크립트 하나를 3dsmaxbatch로 실행한다.

`run_max_tests.py`는 `TEST_SCRIPTS`에 **등록된** 스위트만 돌린다. 프로브는 언더스코어
프리픽스라 등록 대상이 아니므로(`max/max_test_pattern.md` §미지 API 프로브 검증) 별도
진입점이 필요하다.

**종료 코드를 판정 축에 두지 않는다.** `3dsmaxbatch.exe`는 정상 완주해도
`4294967166`(-130)을 낸다. 판정은 프로브가 남긴 **결과 JSON 단독**으로 하고, 종료 코드와
listener 로그는 진단용으로만 읽는다(`patterns/subprocess_verdict_axis.md`).

실행:
    uv run python tests/_run_probe.py _probe_missing_asset.py [타임아웃초]
"""

import importlib.util
import sys
from pathlib import Path

_srcPath = str(Path(__file__).resolve().parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

# MaxTestRunner를 패키지 경유로 import하면 pymxs 의존 모듈까지 딸려 온다.
_maxTestRunnerPath = (
    Path(__file__).resolve().parent.parent / "src" / "pyjallib" / "max" / "maxTestRunner.py"
)
_spec = importlib.util.spec_from_file_location("maxTestRunner", _maxTestRunnerPath)
_maxTestRunnerModule = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_maxTestRunnerModule)
MaxTestRunner = _maxTestRunnerModule.MaxTestRunner

MAX_PATH = Path(r"C:\Program Files\Autodesk\3ds Max 2024")
TESTS_DIR = Path(__file__).resolve().parent / "max"
LOG_DIR = Path(__file__).resolve().parent / "logs"
DEFAULT_TIMEOUT = 1800


def main() -> None:
    """인자로 받은 프로브 스크립트를 실행하고 진단 정보를 출력한다."""
    if len(sys.argv) < 2:
        print("사용법: uv run python tests/_run_probe.py <스크립트명> [타임아웃초]")
        sys.exit(2)

    scriptPath = TESTS_DIR / sys.argv[1]
    if not scriptPath.exists():
        print(f"[FAIL] 스크립트 없음: {scriptPath}")
        sys.exit(2)

    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TIMEOUT
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"3DS Max: {MAX_PATH}")
    print(f"스크립트: {scriptPath}")
    print(f"타임아웃: {timeout}초")
    print("=" * 60)

    runner = MaxTestRunner(MAX_PATH)
    result = runner.run(scriptPath, LOG_DIR, inTimeout=timeout)

    print("=" * 60)
    print(f"종료 코드: {getattr(result, 'return_code', None)} (판정 축 아님)")
    print(f"listener 로그: {getattr(result, 'listener_log_path', None)}")
    print("판정은 프로브가 남긴 결과 JSON을 직접 읽어서 한다.")


if __name__ == "__main__":
    main()
