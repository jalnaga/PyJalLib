#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Missing Asset 프로브 - 정적 사전 정찰 (P0-10 후보 좁히기).

**3ds Max를 기동하지 않는다.** `.max` 파일 바이트열에서 UTF-16LE 문자열을 뽑아
애셋 경로처럼 보이는 것만 남기고 `os.path.exists`로 부재를 센다
(`max/max_test_pattern.md` §`.max` 파일에서 Max 없이 노드 이름을 뽑는 1차 정찰).

**이 스캔은 확정이 아니라 후보 좁히기다.** 정적 스캔의 한계를 결과에 명시적으로 싣는다.

- 압축 저장된 `.max`는 문자열이 안 나온다 -> `scannable is False`로 갈라 둔다.
  0건과 "못 읽었다"를 합치면 대상이 조용히 빠진다(`maxFileScan` dataclass docstring).
- 상대 경로·맨 파일명은 Max의 애셋 탐색 경로를 모르면 해결할 수 없다 -> 별도 채널로 센다.
- 문자열이 살아 있어도 그것이 **현재 참조되는 애셋**이라는 보장이 없다(지워진 머티리얼의
  잔재일 수 있다). 그래서 확정은 씬 로드(`_probe_missing_asset.py` 섹션 H)가 한다.

실행:
    uv run python tests/_probe_missing_asset_static.py

결과:
    tests/logs/probe_missing_asset_static.json
"""

import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

_srcPath = str(Path(__file__).resolve().parent.parent / "src")
if _srcPath not in sys.path:
    sys.path.insert(0, _srcPath)

from pyjallib.maxFileScan import (  # noqa: E402
    _extract_utf16_strings,
    _read_max_bytes,
)

#: 프로덕션 캐릭터 루트. P4 클라이언트 `DongseokKim_DevStorage`의 로컬 루트 아래.
SCENE_ROOT = Path(r"E:/DevStorage_root/DevStorage/Characters")

#: 표본에서 제외할 최상위 카테고리. 이름 그대로 무효 자산 보관소다.
EXCLUDED_CATEGORIES = {"ZZZZ9999_Invalid"}

#: 카테고리당 표본 상한. n=1로 규칙을 정하지 않기 위한 계층 표본이다.
PER_CATEGORY_LIMIT = 12

#: 이 크기를 넘는 파일은 정적 스캔에서 건너뛴다(I/O 비용). 건너뛴 사실은 결과에 남긴다.
MAX_SCAN_BYTES = 80 * 1024 * 1024

#: 애셋으로 볼 확장자. 3ds Max가 외부 파일로 물 수 있는 것들.
ASSET_EXTENSIONS = (
    ".png", ".tga", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".exr",
    ".dds", ".psd", ".hdr", ".ifl", ".gif", ".rgb", ".rla", ".rpf",
    ".max", ".fx", ".mov", ".avi", ".mp4", ".abc", ".vrmesh", ".ies",
)

#: 드라이브 문자 또는 UNC로 시작하는 절대 경로인가.
_ABSOLUTE_PATTERN = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")

LOG_DIR = Path(__file__).resolve().parent / "logs"
RESULT_PATH = LOG_DIR / "probe_missing_asset_static.json"


def _looks_like_asset(inText: str) -> bool:
    """문자열이 애셋 파일 경로처럼 보이는지 판정한다.

    Args:
        inText: 후보 문자열

    Returns:
        알려진 애셋 확장자로 끝나면 True
    """
    if len(inText) < 5:
        return False
    return inText.lower().endswith(ASSET_EXTENSIONS)


def _collect_sample() -> "tuple[list[Path], dict]":
    """카테고리별 계층 표본을 모은다.

    Returns:
        `(표본 경로 목록, 모집단 통계)` 튜플
    """
    population = Counter()
    byCategory = {}

    for scenePath in SCENE_ROOT.rglob("*.max"):
        try:
            category = scenePath.relative_to(SCENE_ROOT).parts[0]
        except (ValueError, IndexError):
            continue
        population[category] += 1
        if category in EXCLUDED_CATEGORIES:
            continue
        byCategory.setdefault(category, []).append(scenePath)

    sample = []
    for category in sorted(byCategory):
        paths = sorted(byCategory[category], key=lambda item: str(item).lower())
        # 앞에서 자르지 않고 균등 간격으로 뽑는다 - 같은 폴더만 담기는 것을 막는다.
        if len(paths) <= PER_CATEGORY_LIMIT:
            picked = paths
        else:
            step = len(paths) / float(PER_CATEGORY_LIMIT)
            picked = [paths[int(index * step)] for index in range(PER_CATEGORY_LIMIT)]
        sample.extend(picked)

    stats = {
        "populationTotal": sum(population.values()),
        "populationByCategory": dict(sorted(population.items())),
        "excludedCategories": sorted(EXCLUDED_CATEGORIES),
        "perCategoryLimit": PER_CATEGORY_LIMIT,
        "sampleSize": len(sample),
    }
    return sample, stats


def _scan_one(inScenePath: Path) -> dict:
    """`.max` 하나를 정적 스캔해 애셋 후보와 부재 건수를 센다.

    Args:
        inScenePath: 스캔할 `.max` 경로

    Returns:
        스캔 결과 dict. `scannable is False`면 건수는 판정 근거가 되지 못한다.
    """
    sizeBytes = 0
    try:
        sizeBytes = inScenePath.stat().st_size
    except OSError:
        pass

    record = {
        "path": str(inScenePath),
        "sizeBytes": sizeBytes,
        "scannable": False,
        "reason": None,
        "absoluteTotal": 0,
        "absoluteMissing": 0,
        "relativeTotal": 0,
        "missingByExtension": {},
        "missingSamples": [],
    }

    if sizeBytes > MAX_SCAN_BYTES:
        record["reason"] = "too_large"
        return record

    data, reason = _read_max_bytes(str(inScenePath))
    if data is None:
        record["reason"] = reason
        return record

    strings = _extract_utf16_strings(data)
    if not strings:
        # 압축 저장 등으로 문자열이 안 나온 경우. 0건과 구분해 남긴다.
        record["reason"] = "no_strings"
        return record

    record["scannable"] = True

    absolutePaths = set()
    relativeNames = set()
    for text in strings:
        if not _looks_like_asset(text):
            continue
        if _ABSOLUTE_PATTERN.match(text):
            absolutePaths.add(text)
        else:
            relativeNames.add(text)

    missingByExtension = Counter()
    missingSamples = []
    for assetPath in sorted(absolutePaths):
        if os.path.exists(assetPath):
            continue
        extension = os.path.splitext(assetPath)[1].lower()
        missingByExtension[extension] += 1
        if len(missingSamples) < 5:
            missingSamples.append(assetPath)

    record["absoluteTotal"] = len(absolutePaths)
    record["absoluteMissing"] = sum(missingByExtension.values())
    record["relativeTotal"] = len(relativeNames)
    record["missingByExtension"] = dict(sorted(missingByExtension.items()))
    record["missingSamples"] = missingSamples
    return record


def main() -> None:
    """표본을 정적 스캔하고 결과를 JSON으로 남긴다."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not SCENE_ROOT.is_dir():
        RESULT_PATH.write_text(
            json.dumps(
                {"ok": False, "error": f"SCENE_ROOT 없음: {SCENE_ROOT}"},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[FAIL] SCENE_ROOT 없음: {SCENE_ROOT}")
        return

    startedAt = time.time()
    sample, stats = _collect_sample()
    print(f"모집단 {stats['populationTotal']}개 / 표본 {len(sample)}개")

    records = []
    for index, scenePath in enumerate(sample, start=1):
        record = _scan_one(scenePath)
        records.append(record)
        flag = "OK " if record["scannable"] else "SKIP"
        print(
            f"[{index:3d}/{len(sample)}] {flag} missing={record['absoluteMissing']:4d}"
            f" / abs={record['absoluteTotal']:4d} rel={record['relativeTotal']:4d}"
            f"  {scenePath.name}"
        )

    scanned = [item for item in records if item["scannable"]]
    withMissing = [item for item in scanned if item["absoluteMissing"] > 0]

    extensionTotals = Counter()
    for item in scanned:
        for extension, count in item["missingByExtension"].items():
            extensionTotals[extension] += count

    summary = {
        "scannedCount": len(scanned),
        "unscannableCount": len(records) - len(scanned),
        "unscannableReasons": dict(
            sorted(Counter(
                item["reason"] for item in records if not item["scannable"]
            ).items())
        ),
        "scenesWithMissing": len(withMissing),
        "scenesWithMissingRatio": (
            round(len(withMissing) / float(len(scanned)), 4) if scanned else None
        ),
        "missingTotal": sum(item["absoluteMissing"] for item in scanned),
        "missingByExtension": dict(sorted(extensionTotals.items())),
        "missingPerSceneMax": max(
            (item["absoluteMissing"] for item in scanned), default=0
        ),
        "relativeOnlyTotal": sum(item["relativeTotal"] for item in scanned),
        "elapsedSeconds": round(time.time() - startedAt, 2),
    }

    RESULT_PATH.write_text(
        json.dumps(
            {"ok": True, "population": stats, "summary": summary, "scenes": records},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=" * 60)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"결과: {RESULT_PATH}")


if __name__ == "__main__":
    main()
