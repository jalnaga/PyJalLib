#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
임포트 결과 JSON 기록 모듈

UE5 헤드레스는 툴과 별개의 프로세스라 반환값을 직접 주고받을 수 없다.
템플릿 스크립트가 임포트 결과(성공 여부, 연 파일 절대경로)를 JSON 파일로 남기면
툴이 subprocess 종료 후 회수한다. 이 목록이 에디터 밖 체인지리스트 이동
(`pyjallib.perforce.Perforce.move_opened_files_to_new_change_list`)의 입력이다.

경로를 사전 계산하지 않고 임포터가 실제로 연 파일을 그대로 넘기므로,
의존성 부수 체크아웃이 목록에서 누락되지 않는다.

의존성: 파이썬 표준 라이브러리 + unreal 모듈만 사용
"""

import json
from pathlib import Path
from typing import List, Optional

import unreal


def collect_opened_files(inResults: List[dict]) -> List[str]:
    """임포트 결과 목록에서 연 파일 절대경로의 합집합을 만듭니다.

    입력 순서를 보존하며 중복을 제거한다 (여러 에셋이 같은 스켈레톤을
    dirty dep으로 공유하면 같은 경로가 반복 등장한다).

    Args:
        inResults: 임포터가 돌려준 결과 딕셔너리 리스트

    Returns:
        list[str]: 중복 없는 연 파일 절대경로 리스트
    """
    mergedPaths = []
    for result in inResults:
        if not isinstance(result, dict):
            continue
        for filePath in result.get("OpenedFiles", []):
            if filePath not in mergedPaths:
                mergedPaths.append(filePath)
    return mergedPaths


def write_import_result(inResultJsonPath: Optional[str], inResults: List[dict],
                        inSuccess: bool = True, inError: Optional[str] = None) -> bool:
    """임포트 결과를 JSON 파일로 기록합니다.

    결과 경로가 비어 있으면 기록을 생략한다 (선택 키 - 구 툴 하위호환).
    기록 실패는 임포트 자체를 실패로 만들지 않도록 에러 로그만 남기고 False를
    반환한다. 반대로 임포트 실패는 호출하는 템플릿이 예외를 그대로 전파해야
    한다 - 툴은 stdout 에러 마커로 실패를 판정하기 때문이다.

    Args:
        inResultJsonPath: 결과 JSON 파일 경로. 빈 값이면 기록 생략.
        inResults: 임포터가 돌려준 결과 딕셔너리 리스트
        inSuccess: 임포트 전체 성공 여부. 기본값 True.
        inError: 실패 사유 문자열. 성공 시 None.

    Returns:
        bool: 기록에 성공하면 True, 생략하거나 실패하면 False
    """
    if not inResultJsonPath:
        unreal.log("[importResultWriter] 결과 JSON 경로가 없어 기록을 생략함")
        return False

    payload = {
        "success": inSuccess,
        "error": inError,
        "results": inResults,
        "openedFiles": collect_opened_files(inResults),
    }

    try:
        outputPath = Path(inResultJsonPath)
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        with open(outputPath, "w", encoding="utf-8") as resultFile:
            json.dump(payload, resultFile, ensure_ascii=False, indent=2)
    except OSError as e:
        unreal.log_error(f"[importResultWriter] 결과 JSON 기록 실패 ({inResultJsonPath}): {e}")
        return False

    unreal.log(
        f"[importResultWriter] 결과 JSON 기록: {inResultJsonPath} "
        f"(결과 {len(inResults)}건, 연 파일 {len(payload['openedFiles'])}개, success={inSuccess})"
    )
    return True
