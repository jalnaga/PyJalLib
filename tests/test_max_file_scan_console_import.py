# -*- coding: utf-8 -*-
"""pyjallib.maxFileScan 콘솔 import 회귀 가드 (Type A).

이 스캐너는 **Max 없이 import와 기능 실행이 가능해야 한다**. `pyjallib.max`도
lazy import 계약에 따라 콘솔에서 로드되지만, 실제 DCC 클래스에 접근하면 pymxs가
필요하다. 부모 패키지 로드와 DCC 기능 접근의 경계를 별도로 검증한다.

`conftest.py`가 `pymxs`를 mock으로 등록하므로 **같은 프로세스 안에서는 이 회귀를 잡을 수
없다.** 그래서 `subprocess`로 mock 없는 진짜 콘솔 환경을 띄워 단정한다.
"""

from pathlib import Path
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


def test_console_import_of_pyjallib_max_defers_dcc_until_morph_access():
    """실제 부모 패키지는 DCC 없이 로드되고 Morph 접근은 pymxs 부재로 실패한다."""
    expectedPath = Path(__file__).resolve().parents[1] / "src/pyjallib/max/__init__.py"
    result = _run_console(f"""
from pathlib import Path
import sys
assert not any(n.startswith(('pymxs', 'PySide', 'qtmax')) for n in sys.modules)
import pyjallib.max as targetModule
assert Path(targetModule.__file__).resolve() == Path({str(expectedPath)!r}).resolve(), targetModule.__file__
assert not any(n.startswith(('pymxs', 'PySide', 'qtmax')) for n in sys.modules), sorted(sys.modules)
try:
    targetModule.Morph
except ModuleNotFoundError as error:
    assert error.name == 'pymxs', repr(error)
else:
    raise AssertionError('pymxs 없는 콘솔에서 Morph 접근이 성공했다')
""")

    assert result.returncode == 0, f"지연 로딩 경계 검증 실패: {result.stderr}"


def test_max_file_scan_module_source_has_no_pymxs_import():
    """모듈 소스에 pymxs import가 들어오지 못하게 막는다."""
    import pyjallib.maxFileScan as targetModule

    with open(targetModule.__file__, encoding="utf-8") as f:
        source = f.read()

    assert "import pymxs" not in source
    assert "from pymxs" not in source
