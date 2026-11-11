# -*- coding: utf-8 -*-
"""pdoc으로 pyjallib API 문서(HTML)를 생성한다.

`generate_docs.ps1`이 호출한다. 직접 실행할 때는 저장소 루트에서 다음처럼 쓴다.

    uv run --with pdoc python docs_support/build_docs.py --output docs

pyjallib의 일부 모듈은 3ds Max(`pymxs`, `qtmax`)나 Unreal Editor(`unreal`) 안에서만 import할
수 있다. 문서 생성은 그 프로그램 밖에서 하므로 해당 모듈을 mock으로 등록한 뒤 pdoc을 돌린다.
import하지 못한 모듈이 하나라도 있으면 문서가 빠진 채 성공으로 끝나지 않도록 실패 처리한다.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import List, Optional, Sequence
from unittest.mock import MagicMock

PACKAGE_NAME = "pyjallib"

# 호스트 프로그램 안에서만 존재하는 모듈. import 전에 mock으로 등록한다.
HOST_ONLY_MODULES = ("pymxs", "pymxs.runtime", "qtmax", "unreal")

# 문서에서 빼는 모듈(pdoc 제외 패턴). Unreal 실행 템플릿은 자리표시자를 채워 Unreal 안에서
# 실행하는 스크립트라서 import하면 본문이 그대로 실행된다.
EXCLUDED_MODULE_PATTERNS = (r"!pyjallib\.ue5\.templates\.",)


def build_docs(inSourceRoot: Path, inOutputDirectory: Path) -> List[str]:
    """문서를 생성하고 pdoc이 낸 경고 문구 목록을 돌려준다.

    Args:
        inSourceRoot: `src/pyjallib`이 들어 있는 저장소 루트
        inOutputDirectory: HTML을 쓸 디렉터리

    Returns:
        생성 중 나온 경고 문구 목록. 비어 있으면 모든 모듈을 문서화한 것이다.
    """
    sourceDirectory = inSourceRoot / "src"
    if not (sourceDirectory / PACKAGE_NAME / "__init__.py").is_file():
        raise FileNotFoundError(f"{sourceDirectory / PACKAGE_NAME} 패키지를 찾을 수 없습니다.")

    for moduleName in HOST_ONLY_MODULES:
        sys.modules.setdefault(moduleName, MagicMock())
    # Unreal 안에서 쓰는 모듈은 같은 디렉터리의 모듈을 최상위 이름으로 import한다.
    sys.path.insert(0, str(sourceDirectory / PACKAGE_NAME / "ue5" / "inUnreal"))
    # 설치된 사본이 아니라 지정한 소스를 문서화한다.
    sys.path.insert(0, str(sourceDirectory))

    import pdoc

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pdoc.pdoc(PACKAGE_NAME, *EXCLUDED_MODULE_PATTERNS, output_directory=inOutputDirectory)
    return [str(item.message) for item in caught]


def main(inArgv: Optional[Sequence[str]] = None) -> int:
    """명령줄 진입점.

    Args:
        inArgv: 인자 목록. None이면 `sys.argv[1:]`.

    Returns:
        종료 코드. 성공 0, 실패 1.
    """
    parser = argparse.ArgumentParser(description="pyjallib API 문서를 생성합니다.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="src/pyjallib이 들어 있는 저장소 루트(기본: 이 스크립트의 상위 디렉터리)",
    )
    parser.add_argument("--output", type=Path, required=True, help="HTML을 쓸 디렉터리")
    args = parser.parse_args(inArgv)

    try:
        warningMessages = build_docs(args.source_root.resolve(), args.output.resolve())
    except Exception as error:  # 어떤 실패든 0이 아닌 코드로 끝낸다
        print(f"문서 생성에 실패했습니다: {error}", file=sys.stderr)
        return 1
    if warningMessages:
        for message in warningMessages:
            print(f"경고: {message}", file=sys.stderr)
        print(f"문서 생성 중 경고 {len(warningMessages)}건이 있어 실패로 처리합니다.", file=sys.stderr)
        return 1
    print(f"문서를 생성했습니다: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
