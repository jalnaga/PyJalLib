#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
네이티브 C++ 모듈 빌드 스크립트 - ``pyjallib.native.alpha_wrap_native`` (Alpha Wrap).

pyjallib 패키지 빌드(hatchling)와 분리한다 - 빌드 백엔드를 scikit-build-core로 바꾸면 pyjallib 전체 빌드가 바뀐다.
빌드 도구(nanobind·CMake)는 uv가 만드는 **빌드 전용 임시 환경**에서 받고, pyjallib 의존성에는 넣지 않는다.
벤더링 사본(``native/alphaWrap``)만 컴파일하므로 네트워크는 도구를 받을 때만 탄다.

산출물은 ``src/pyjallib/native/``에 두고 git으로 추적한다(P4 배포 매핑이 ``src/pyjallib``이고, 새 워크트리에서 빌드 없이
테스트가 돌아야 한다). 업스트림 LICENSE 사본도 같은 폴더에 둔다. 빌드 바이트는 재현되지 않으므로 바뀌었는지는 소스
이력과 모듈의 출처 속성(``UPSTREAM_COMMIT`` 등)으로 판정한다.

요구: Windows x64, Visual Studio 2022(C++ 워크로드), uv. 대상 ABI는 CPython 3.10(3ds Max 2024 내장 Python과 같다).

사용법(PyJalLib 루트에서):
    uv run --no-project --python 3.10 --with nanobind==3.1.0 --with cmake python native/build_native.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_PROJ_ROOT = Path(__file__).resolve().parent.parent
_SOURCE_DIR = _PROJ_ROOT / "native" / "alphaWrap"
_DEST_DIR = _PROJ_ROOT / "src" / "pyjallib" / "native"
_MODULE = "alpha_wrap_native"
_LICENSE_DEST = "alpha_wrap_LICENSE.txt"
_GENERATOR = ["-G", "Visual Studio 17 2022", "-A", "x64"]


def _check_environment() -> str:
    """빌드 인터프리터·도구를 확인하고 nanobind CMake 경로를 돌려준다."""
    if sys.version_info[:2] != (3, 10):
        raise SystemExit(f"[ERROR] CPython 3.10에서 실행해야 한다(현재 {sys.version.split()[0]})")
    try:
        import nanobind
    except ImportError as exc:
        raise SystemExit("[ERROR] nanobind가 없다 - 사용법의 uv run --with 명령으로 실행한다") from exc
    if shutil.which("cmake") is None:
        raise SystemExit("[ERROR] cmake가 없다 - 사용법의 uv run --with 명령으로 실행한다")
    return nanobind.cmake_dir()


def _verify(inPyd: Path) -> None:
    """빌드한 .pyd를 새 프로세스에서 import해 출처 속성과 정육면체 감싸기를 확인한다."""
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import alpha_wrap_native as m; "
        "v=[0,0,0, 1,0,0, 1,1,0, 0,1,0, 0,0,1, 1,0,1, 1,1,1, 0,1,1]; "
        "t=[0,2,1, 0,3,2, 4,5,6, 4,6,7, 0,1,5, 0,5,4, 1,2,6, 1,6,5, 2,3,7, 2,7,6, 3,0,4, 3,4,7]; "
        "ov, of, st = m.wrap(v, t, 0.2, 0.02); "
        "print(m.UPSTREAM_COMMIT, m.PREDICATES_COMMIT, m.RUNTIME, len(of) // 3, st['output_faces'])"
    )
    result = subprocess.run([sys.executable, "-c", code, str(inPyd.parent)], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"[ERROR] 빌드 산출물 import 실패:\n{result.stderr}")
    print(f"검증: {result.stdout.strip()}")


def main() -> int:
    """벤더링 사본을 MSVC Release로 빌드하고 산출물을 src/pyjallib/native/로 복사한다."""
    nanobindDir = _check_environment()
    with tempfile.TemporaryDirectory(prefix="pyjallib_alpha_wrap_") as tmp:
        buildDir = Path(tmp)
        print("=== CMake configure ===")
        configure = [
            "cmake", "-S", str(_SOURCE_DIR), "-B", str(buildDir), *_GENERATOR,
            f"-DPython_EXECUTABLE={sys.executable}", f"-Dnanobind_DIR={nanobindDir}",
        ]
        if subprocess.run(configure).returncode != 0:
            print("[ERROR] CMake configure 실패")
            return 1
        print("\n=== CMake build (Release) ===")
        if subprocess.run(["cmake", "--build", str(buildDir), "--config", "Release", "--parallel"]).returncode != 0:
            print("[ERROR] CMake build 실패")
            return 1
        built = sorted(buildDir.glob(f"Release/{_MODULE}*.pyd"))
        if len(built) != 1:
            print(f"[ERROR] .pyd를 하나로 특정하지 못했다: {built}")
            return 1
        _DEST_DIR.mkdir(parents=True, exist_ok=True)
        dest = _DEST_DIR / built[0].name
        shutil.copy2(str(built[0]), str(dest))
        shutil.copy2(str(_SOURCE_DIR / "LICENSE"), str(_DEST_DIR / _LICENSE_DEST))
    print(f"\n  -> {dest} ({dest.stat().st_size:,} bytes)")
    _verify(dest)
    print(f"\n=== 빌드 완료: {dest.name} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
