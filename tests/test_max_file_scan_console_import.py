# -*- coding: utf-8 -*-
"""pyjallib.maxFileScan 콘솔 import 회귀 가드 (Type A).

이 스캐너의 존재 가치는 **Max 없이 도는 것**이다. `pyjallib.max` 아래로 흘러가면
부모 `__init__`이 39개 pymxs 모듈을 즉시 import하므로 정확히 그 환경에서 import가
불가능해지고 모듈의 존재 의미가 사라진다.

`conftest.py`가 `pymxs`를 mock으로 등록하므로 **같은 프로세스 안에서는 이 회귀를 잡을 수
없다.** 그래서 `subprocess`로 mock 없는 진짜 콘솔 환경을 띄워 단정한다.
"""

import subprocess
import sys


def _run_console(inCode: str) -> subprocess.CompletedProcess:
    """mock 없는 별도 파이썬 프로세스에서 코드를 실행한다.

    Args:
        inCode: 실행할 파이썬 코드

    Returns:
        실행 결과
    """
    return subprocess.run(
        [sys.executable, "-c", inCode],
        capture_output=True,
        text=True,
    )


def test_console_environment_really_has_no_pymxs():
    """이 가드가 도는 환경에 pymxs가 정말 없는지 먼저 단정한다.

    pymxs가 import되는 환경이면 아래 가드는 **무엇도 증명하지 못한다**(공허한 통과).
    그래서 환경 자체를 먼저 못 박는다.
    """
    result = _run_console(
        "import importlib.util as u; "
        "assert u.find_spec('pymxs') is None, 'pymxs가 import 가능한 환경이다'; "
        "print('NO_PYMXS')"
    )

    assert result.returncode == 0, f"환경 확인 실패: {result.stderr}"
    assert "NO_PYMXS" in result.stdout


def test_console_import_of_max_file_scan_succeeds_without_pymxs():
    """콘솔에서 pyjallib.maxFileScan import가 pymxs 없이 성공한다."""
    result = _run_console(
        "from pyjallib.maxFileScan import scan_node_names, scan_layer_names, count_names; "
        "from pyjallib.maxFileScan import MaxFileScanResult; "
        "r = scan_node_names('__no_such_file__.max'); "
        "assert r.scannable is False; "
        "print('OK')"
    )

    assert result.returncode == 0, f"콘솔 import 실패: {result.stderr}"
    assert "OK" in result.stdout


def test_console_import_of_pyjallib_max_still_fails():
    """대조군 - `pyjallib.max` 아래는 콘솔에서 여전히 import가 깨진다.

    이 대조가 위 가드의 판별력이다. 둘 다 성공하면 "pymxs가 없어도 다 된다"는 뜻이라
    배치 결정을 지지하지 못한다.
    """
    result = _run_console("import pyjallib.max")

    assert result.returncode != 0
    assert "pymxs" in result.stderr


def test_max_file_scan_module_source_has_no_pymxs_import():
    """모듈 소스에 pymxs import가 들어오지 못하게 막는다."""
    import pyjallib.maxFileScan as targetModule

    with open(targetModule.__file__, encoding="utf-8") as f:
        source = f.read()

    assert "import pymxs" not in source
    assert "from pymxs" not in source
