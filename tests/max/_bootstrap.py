# -*- coding: utf-8 -*-
"""Type C 공용 부트스트랩 - 이 체크아웃의 소스를 로드하고 그것을 단정한다.

**왜 필요한가.** 3ds Max는 기동 시 배포본 `pyjallib`을 `sys.modules`에 **선점**한다.
그래서 `sys.path.insert`만 해서는 캐시 히트로 **배포본이 검증된다** - 워크트리에서
고친 코드는 한 줄도 실행되지 않는데 테스트는 초록으로 통과한다
(`processes/worktree_workflow.md` §2-repo).

16차 복기 세션 3 시점 실측: `tests/max/` Type C 21개 중 **10개가 퍼지 없이** 돌고 있었다.
그 10개는 "무엇을 검증했는지 말할 수 없는" 상태였다.

**쓰는 법.** 테스트 스크립트 최상단(다른 `pyjallib` import보다 **앞**)에서 부른다.

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import bootstrap_pyjallib

_SRC = bootstrap_pyjallib()      # 퍼지 + 경로 선주입, 로드될 소스 경로를 돌려준다

import pyjallib                   # 이제부터 이 체크아웃의 소스다
from pyjallib.testKit import TestReporter
```

그리고 **TC00으로 출처를 단정한다** - 단정이 없으면 아무것도 검증하지 않은 것이 된다.

```python
reporter.assert_test(
    "TC00: 로드 출처가 이 체크아웃인가",
    assert_loaded_from_checkout(pyjallib),
    f"pyjallib.__file__={pyjallib.__file__}",
)
```
"""

import os
import sys
from pathlib import Path

#: 배포본 검증용 경로 오버라이드. 완료 게이트에서 **배포처**를 검증할 때만 쓴다.
#:
#: `MaxTestRunner._build_env`가 `PYTHONPATH`를 **지우기** 때문에 그 통로로는 DCC 세션에
#: 닿지 않는다. 전용 환경변수는 그대로 전달된다. 변수가 없으면 이 체크아웃으로 떨어지므로
#: **배포본 검증과 워크트리 검증을 같은 코드가 자동 추종**한다.
_SRC_ENV = "PYJALLIB_SRC_OVERRIDE"


def checkout_src_path() -> Path:
    """검증 대상 `src` 디렉토리 경로를 돌려준다.

    Returns:
        `PYJALLIB_SRC_OVERRIDE`가 있으면 그 경로, 없으면 `<repo>/src`
    """
    override = os.environ.get(_SRC_ENV)
    if override:
        return Path(override).resolve()
    return (Path(__file__).resolve().parent.parent.parent / "src").resolve()


#: 지금 무엇을 검증하고 있는지. 배포본 검증에서는 "deployment"가 된다.
TARGET_LABEL = "deployment" if os.environ.get(_SRC_ENV) else "worktree"


def bootstrap_pyjallib() -> Path:
    """배포본 선점을 퍼지하고 이 체크아웃의 `src`를 `sys.path` 맨 앞에 둔다.

    `sys.path` 조작만으로는 부족하다 - 이미 `sys.modules`에 올라온 `pyjallib.*`을
    **전부 지워야** 다음 import가 디스크를 다시 본다.

    Returns:
        선주입한 `src` 경로
    """
    srcPath = checkout_src_path()
    srcText = str(srcPath)
    while srcText in sys.path:
        sys.path.remove(srcText)
    sys.path.insert(0, srcText)

    for moduleName in [
        name for name in list(sys.modules) if name.split(".")[0] == "pyjallib"
    ]:
        del sys.modules[moduleName]
    return srcPath


def assert_loaded_from_checkout(inModule) -> bool:
    """모듈이 **검증 대상 소스**에서 로드됐는지 판정한다.

    보통은 이 체크아웃의 `src`다. 완료 게이트에서 `PYJALLIB_SRC_OVERRIDE`를 주면
    **배포처**가 되고, 그때는 같은 함수가 배포본을 단정한다. 호출부의 TC00 문구는
    "이 체크아웃"이라고 적혀 있지만 실제 축은 `TARGET_LABEL`이 말하는 대상이고,
    상세 문구에 찍히는 `__file__`이 어느 쪽인지 드러낸다.

    `__version__`을 축으로 쓰면 오판한다 - `pyproject.toml`보다 stale할 수 있다
    (2026-09-18 실측: `__version__` 0.3.3 vs 선언 0.3.5). **`__file__`을 본다.**

    Args:
        inModule: 검사할 모듈(보통 `pyjallib`)

    Returns:
        모듈 파일이 이 체크아웃의 `src` 아래면 True
    """
    moduleFile = getattr(inModule, "__file__", None)
    if not moduleFile:
        return False
    try:
        Path(moduleFile).resolve().relative_to(checkout_src_path())
    except ValueError:
        return False
    return True
