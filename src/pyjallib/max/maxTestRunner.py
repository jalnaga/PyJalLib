#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3ds Max 전용 테스트 러너 모듈.

TestRunner를 확장하여 3dsmaxbatch.exe로 테스트를 실행한다.
pymxs에 의존하지 않으며, 순수 subprocess 관리만 담당한다.

의존성: Python stdlib + pyjallib.testKit.testRunner
"""

from pathlib import Path
from typing import Optional

from pyjallib.testKit.testRunner import RunResult, TestRunner


class MaxTestRunner(TestRunner):
    """3dsmaxbatch.exe를 이용한 3ds Max 전용 테스트 러너.

    3dsmaxbatch.exe의 명령줄 옵션(-mxsString, -sceneFile, -listenerlog, -silent)을
    자동으로 구성하여 헤드리스 배치 테스트를 실행한다.

    Example:
        runner = MaxTestRunner(Path("C:/Program Files/Autodesk/3ds Max 2025"))
        result = runner.run(
            Path("tests/max/test_bone.py"),
            Path("tests/logs"),
            inSceneFile=Path("tests/fixtures/test_scene.max"),
        )
    """

    def __init__(self, inMaxPath: Path) -> None:
        """3ds Max 러너를 초기화한다.

        Args:
            inMaxPath: 3ds Max 설치 디렉토리 경로 (3dsmaxbatch.exe가 있는 폴더)
        """
        batchPath = Path(inMaxPath) / "3dsmaxbatch.exe"
        super().__init__(batchPath)

    def build_command(
        self,
        inScriptPath: Path,
        inSceneFile: Optional[Path] = None,
        inListenerLog: Optional[Path] = None,
        **kwargs: object,
    ) -> list[str]:
        """부모 클래스의 build_command를 확장하여 3dsmaxbatch.exe 전용 인수를 추가한다.

        부모 TestRunner.build_command(inScriptPath, **kwargs) 시그니처에
        inSceneFile, inListenerLog 파라미터를 추가하여 3ds Max 배치 실행에
        필요한 -sceneFile, -mxsString, -listenerlog, -silent 옵션을 구성한다.
        run() 메서드가 super().run()을 통해 이 메서드를 호출할 때
        kwargs로 inSceneFile, inListenerLog가 전달된다.

        Args:
            inScriptPath: 실행할 Python 테스트 스크립트 경로
            inSceneFile: 로드할 장면 파일(.max) 경로. None이면 빈 씬에서 실행.
            inListenerLog: MAXScript Listener 로그 파일 경로
            **kwargs: 추가 옵션 (무시됨)

        Returns:
            3dsmaxbatch.exe 명령줄 인수 리스트
        """
        cmd: list[str] = [str(self._executablePath)]

        if inSceneFile is not None:
            cmd += ["-sceneFile", str(inSceneFile)]

        # MaxScript를 통한 Python 스크립트 실행
        mxsCommand = f'python.ExecuteFile @"{str(inScriptPath)}"'
        cmd += ["-mxsString", mxsCommand]

        if inListenerLog is not None:
            cmd += ["-listenerlog", str(inListenerLog)]

        cmd += ["-silent"]
        return cmd

    def run(
        self,
        inScriptPath: Path,
        inLogDir: Path,
        inSceneFile: Optional[Path] = None,
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
            inSceneFile: 로드할 장면 파일(.max) 경로. None이면 빈 씬에서 실행.
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
        # inSceneFile과 inListenerLog를 kwargs로 전달
        runResult = super().run(
            inScriptPath,
            inLogDir,
            inTimeout=inTimeout,
            inSceneFile=inSceneFile,
            inListenerLog=listenerLogPath,
            **kwargs,
        )

        # listener 로그 경로를 결과에 설정
        runResult.listener_log_path = listenerLogPath

        return runResult
