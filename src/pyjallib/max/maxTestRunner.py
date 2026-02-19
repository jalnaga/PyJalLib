#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max 전용 테스트 러너 모듈.

TestRunner를 확장하여 3dsmaxbatch.exe로 테스트를 실행한다.
pymxs에 의존하지 않으며, 순수 subprocess 관리만 담당한다.

의존성: Python stdlib + pyjallib.testKit.testRunner
"""

import os
import re
from pathlib import Path
from typing import Optional

from pyjallib.testKit.testRunner import RunResult, TestRunner


class MaxTestRunner(TestRunner):
    """3dsmaxbatch.exe를 이용한 3ds Max 전용 테스트 러너.

    3dsmaxbatch.exe에 스크립트 파일을 직접 전달하여 헤드리스 배치 테스트를 실행한다.
    3ds Max 2024+ 에서는 스크립트 파일이 첫 번째 필수 인자이며,
    -listenerlog 옵션으로 리스너 로그를 기록할 수 있다.

    Example:
        runner = MaxTestRunner(Path("C:/Program Files/Autodesk/3ds Max 2024"))
        result = runner.run(
            Path("tests/max/test_bone.py"),
            Path("tests/logs"),
        )
    """

    def __init__(self, inMaxPath: Path) -> None:
        """3ds Max 러너를 초기화한다.

        Args:
            inMaxPath: 3ds Max 설치 디렉토리 경로 (3dsmaxbatch.exe가 있는 폴더)
        """
        batchPath = Path(inMaxPath) / "3dsmaxbatch.exe"
        super().__init__(batchPath)

    def _build_env(self) -> Optional[dict[str, str]]:
        """3DS Max 실행을 위한 클린 환경을 구성한다.

        시스템에 설치된 다른 Python 버전(3.12, 3.13 등)의 경로가 3DS Max 내장
        Python 3.10과 충돌하는 것을 방지하기 위해 환경변수를 정리한다.

        Returns:
            정리된 환경변수 딕셔너리
        """
        env = os.environ.copy()

        # PYTHONPATH, PYTHONHOME 제거 (Max가 자체 Python을 사용하도록)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)

        # PATH에서 시스템 Python 경로 제거 (Python310은 유지)
        if "PATH" in env:
            pathSep = os.pathsep
            paths = env["PATH"].split(pathSep)
            cleanedPaths = [
                p for p in paths
                if not re.search(r"Python3(?!10)\d+", p, re.IGNORECASE)
            ]
            env["PATH"] = pathSep.join(cleanedPaths)

        return env

    def build_command(
        self,
        inScriptPath: Path,
        inListenerLog: Optional[Path] = None,
        **kwargs: object,
    ) -> list[str]:
        """3dsmaxbatch.exe 명령줄을 구성한다.

        3ds Max 2024+에서 3dsmaxbatch.exe는 스크립트 파일을 첫 번째 필수 인자로 받고,
        -listenerlog 옵션으로 리스너 로그 경로를 지정한다.

        Args:
            inScriptPath: 실행할 Python(.py) 또는 MAXScript(.ms) 파일 경로
            inListenerLog: MAXScript Listener 로그 파일 경로
            **kwargs: 추가 옵션 (무시됨)

        Returns:
            3dsmaxbatch.exe 명령줄 인수 리스트
        """
        cmd: list[str] = [str(self._executablePath), str(inScriptPath)]

        if inListenerLog is not None:
            cmd += ["-listenerlog", str(inListenerLog)]

        return cmd

    def run(
        self,
        inScriptPath: Path,
        inLogDir: Path,
        inTimeout: int = 300,
        **kwargs: object,
    ) -> RunResult:
        """3dsmaxbatch.exe로 테스트를 실행한다.

        부모 클래스의 subprocess 관리 로직을 재사용하며, listener_log 경로를
        자동 설정하여 build_command에 전달한다. 실행 후 RunResult에
        listener_log_path를 설정한다.

        Args:
            inScriptPath: 실행할 Python 테스트 스크립트 경로
            inLogDir: 로그 파일 저장 디렉토리
            inTimeout: 타임아웃 (초). 기본값 300초.
            **kwargs: 추가 옵션

        Returns:
            프로세스 실행 결과
        """
        logDir = Path(inLogDir)

        # listener 로그 경로 자동 생성
        scriptName = Path(inScriptPath).stem
        listenerLogPath = logDir / f"{scriptName}_listener.log"

        # super().run()이 build_command(**kwargs)를 호출하므로
        # inListenerLog를 kwargs로 전달
        runResult = super().run(
            inScriptPath,
            inLogDir,
            inTimeout=inTimeout,
            inListenerLog=listenerLogPath,
            **kwargs,
        )

        # listener 로그 경로를 결과에 설정
        runResult.listener_log_path = listenerLogPath

        return runResult
