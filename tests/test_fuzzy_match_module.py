# -*- coding: utf-8 -*-
"""pyjallib.fuzzyMatch 모듈 - Type A 테스트.

두 가지를 단정한다.

1. **pymxs 없이 import 가능하다.** 이 모듈이 ``pyjallib.max.ui`` 밑을 떠난 이유가
   그것이므로, 그 성질이 깨지면 이관의 값이 사라진다.
2. **이관 전후 동치.** ``fuzzySearchComboBox``의 기존 밑줄 이름이 새 구현과 같은
   객체를 가리키고, 대표 입력의 스코어가 기대값과 일치한다.

**왜 subprocess인가:** ``tests/conftest.py``가 세션 전역으로 ``pymxs``를
MagicMock으로 sys.modules에 심는다. 따라서 이 파일 안에서 그냥 import를 시도하면
스텁이 이미 깔린 상태라 "pymxs 없이 된다"를 전혀 검증하지 못한다(초록이지만
공허한 통과). 인터프리터를 분리해야만 그 단정이 실효를 갖는다.
"""

import os
import subprocess
import sys
from pathlib import Path

# 워크트리/체크아웃 위치에 무관하게 src를 찾는다 (tests/ 의 형제).
_SRC_DIR = Path(__file__).resolve().parent.parent / "src"


def _run_in_clean_interpreter(inCode: str) -> subprocess.CompletedProcess:
    """conftest 스텁이 없는 별도 인터프리터에서 코드를 실행한다.

    Args:
        inCode: 실행할 파이썬 코드

    Returns:
        완료된 subprocess 결과 (stdout/stderr 캡처됨)
    """
    # Windows 인터프리터는 SYSTEMROOT 등 기본 환경변수 없이는 기동하지 못하므로
    # 현재 환경을 물려받고 PYTHONPATH만 워크트리 src로 덮는다.
    childEnv = os.environ.copy()
    childEnv["PYTHONPATH"] = str(_SRC_DIR)

    return subprocess.run(
        [sys.executable, "-c", inCode],
        capture_output=True,
        text=True,
        env=childEnv,
        cwd=str(_SRC_DIR.parent),
    )


def test_import_without_pymxs_stub():
    """pymxs가 sys.modules에 없는 인터프리터에서 import가 성공한다."""
    code = (
        "import sys\n"
        "from pyjallib.fuzzyMatch import fuzzy_score\n"
        "assert 'pymxs' not in sys.modules, 'pymxs가 로드되었다'\n"
        "assert fuzzy_score('kd', 'KimDokja') > 0\n"
        "print('OK')\n"
    )
    result = _run_in_clean_interpreter(code)
    assert result.returncode == 0, (
        f"pymxs 없는 인터프리터에서 import 실패\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK" in result.stdout


def test_import_from_package_root_without_pymxs_stub():
    """루트 공개 API(``from pyjallib import fuzzy_score``)도 pymxs 없이 된다."""
    code = (
        "import sys\n"
        "from pyjallib import fuzzy_score\n"
        "assert 'pymxs' not in sys.modules, 'pymxs가 로드되었다'\n"
        "assert fuzzy_score('', 'anything') == 0\n"
        "print('OK')\n"
    )
    result = _run_in_clean_interpreter(code)
    assert result.returncode == 0, (
        f"루트 공개 API import 실패\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK" in result.stdout


def test_combo_box_alias_is_same_object():
    """``fuzzySearchComboBox._fuzzy_score``가 이관된 구현과 같은 객체다.

    별칭이 같은 객체가 아니면 두 구현이 공존하는 것이므로, 한쪽만 고쳐도
    다른 쪽이 조용히 남는다. 동치 값 비교로는 그 상태를 잡을 수 없다.
    """
    from pyjallib.fuzzyMatch import fuzzy_score, is_word_start
    from pyjallib.max.ui import fuzzySearchComboBox

    assert fuzzySearchComboBox._fuzzy_score is fuzzy_score
    assert fuzzySearchComboBox._is_word_start is is_word_start


def test_root_export_is_same_object():
    """루트 export도 같은 객체를 가리킨다."""
    import pyjallib
    from pyjallib.fuzzyMatch import fuzzy_score

    assert pyjallib.fuzzy_score is fuzzy_score


def test_score_values_preserved():
    """대표 입력의 스코어가 이관 전 규약과 일치한다.

    빈 패턴 0 / 실패 -1 / 연속 우위 / 단어시작 우위 / 대소문자 무시.
    """
    from pyjallib.fuzzyMatch import fuzzy_score

    # 빈 패턴은 0 (전체 매칭)
    assert fuzzy_score("", "KimDokja") == 0

    # 매칭 실패는 -1
    assert fuzzy_score("xyz", "KimDokja") == -1

    # 매칭 성공은 양수
    assert fuzzy_score("kd", "KimDokja") > 0

    # 연속 매칭이 비연속보다 높다
    assert fuzzy_score("Kim", "KimDokja") > fuzzy_score("KDj", "KimDokja")

    # 대소문자를 구분하지 않는다
    assert fuzzy_score("KIM", "KimDokja") == fuzzy_score("kim", "KimDokja")

    # 부분수열이므로 순서가 뒤바뀌면 실패
    assert fuzzy_score("dk", "Dokja") > 0
    assert fuzzy_score("kD", "Dokja") == -1


def test_word_start_boundaries():
    """단어 시작점 판정 - 첫 문자, camelCase 경계, '_'/'-' 뒤."""
    from pyjallib.fuzzyMatch import is_word_start

    assert is_word_start("KimDokja", 0) is True  # 첫 문자
    assert is_word_start("KimDokja", 3) is True  # 'D' - camelCase 경계
    assert is_word_start("KimDokja", 1) is False  # 'i' - 중간
    assert is_word_start("Bone_L", 5) is True  # '_' 뒤
    assert is_word_start("Bone-L", 5) is True  # '-' 뒤
