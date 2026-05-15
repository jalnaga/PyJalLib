# -*- coding: utf-8 -*-
"""LegacyBaseImporter.is_development_mode() Type A 단위 테스트.

UE5 헤드레스 silent 임포트 실패 회귀 방지 테스트.
PRD: `pyjallib/planning/active_prd.md`
Primary Manual: `.claude/references/ue5/headless_silent_failure_diagnosis.md`

검증 대상 4 케이스 (PRD Acceptance Criteria 1:1 매핑):
    1. `[Development]` 섹션 누락 ini -> False (NoSectionError fallback)
    2. `[Development] mode=true` -> True
    3. `[Development] mode=false` -> False
    4. ini 파일 자체가 없음 -> False

테스트 격리:
    - `tmp_path` fixture로 임시 ini 디렉토리 생성
    - `pathlib.Path.home`을 monkeypatch하여 사용자 환경의 실제 ini를
      절대 읽지 않도록 차단 (회귀 격리의 핵심)
    - `LegacyBaseImporter`가 ABC이므로 더미 서브클래스 인스턴스화
"""

from pathlib import Path

import pytest

from pyjallib.ue5.inUnreal.legacyBaseImporter import LegacyBaseImporter


class _DummyImporter(LegacyBaseImporter):
    """추상 메서드를 빈 구현으로 채운 테스트용 더미 서브클래스."""

    @property
    def asset_type(self) -> str:
        """더미 에셋 타입.

        Returns:
            테스트용 고정 문자열.
        """
        return "Dummy"

    def create_import_task(self, inFbxFile: str, inDestinationPath: str):
        """더미 임포트 태스크 생성 (no-op).

        Args:
            inFbxFile: FBX 파일 경로 (사용하지 않음).
            inDestinationPath: 임포트 대상 경로 (사용하지 않음).

        Returns:
            None.
        """
        return None


def _make_ini(inTmpPath: Path, inContent: str) -> Path:
    """`tmp_path/Documents/ORV/ORV_Setting.ini`를 작성한다.

    Args:
        inTmpPath: pytest의 `tmp_path` fixture 값.
        inContent: ini 본문 문자열.

    Returns:
        생성된 ini 파일의 절대 경로.
    """
    iniDir = inTmpPath / "Documents" / "ORV"
    iniDir.mkdir(parents=True, exist_ok=True)
    iniFile = iniDir / "ORV_Setting.ini"
    iniFile.write_text(inContent, encoding="utf-8")
    return iniFile


def _patch_home(monkeypatch: pytest.MonkeyPatch, inHomePath: Path) -> None:
    """`pathlib.Path.home`을 inHomePath 반환 람다로 교체한다.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        inHomePath: 가짜 홈 디렉토리로 사용할 경로.
    """
    monkeypatch.setattr(Path, "home", lambda: inHomePath)


def _make_importer() -> _DummyImporter:
    """더미 서브클래스 인스턴스를 생성한다.

    `LegacyImporterSettings` 생성자는 conftest.py가 mock으로 주입했으므로
    부작용 없이 인스턴스화된다.

    Returns:
        `_DummyImporter` 인스턴스.
    """
    return _DummyImporter(
        inContentRootPrefix="/tmp/content",
        inFbxRootPrefix="/tmp/fbx",
        inPresetName="TestPreset",
    )


def test_returns_false_when_development_section_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[Development]` 섹션이 없는 ini 환경에서 False를 반환한다.

    NonWork 환경에서 발생한 `NoSectionError`를 fallback으로 흡수하는지
    검증한다. PRD AC1, AC4, AC5 매핑 (회귀 방지의 핵심).
    """
    _make_ini(tmp_path, "[Folder]\nfoo=bar\n")
    _patch_home(monkeypatch, tmp_path)

    importer = _make_importer()
    result = importer.is_development_mode()

    assert result is False
    assert isinstance(result, bool)


def test_returns_true_when_mode_is_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[Development] mode=true` ini 환경에서 True를 반환한다.

    PRD AC2 매핑.
    """
    _make_ini(tmp_path, "[Development]\nmode=true\n")
    _patch_home(monkeypatch, tmp_path)

    importer = _make_importer()
    result = importer.is_development_mode()

    assert result is True
    assert isinstance(result, bool)


def test_returns_false_when_mode_is_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[Development] mode=false` ini 환경에서 False를 반환한다.

    PRD AC3 매핑.
    """
    _make_ini(tmp_path, "[Development]\nmode=false\n")
    _patch_home(monkeypatch, tmp_path)

    importer = _make_importer()
    result = importer.is_development_mode()

    assert result is False
    assert isinstance(result, bool)


def test_returns_false_when_ini_file_does_not_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ini 파일 자체가 없는 환경에서 False를 반환한다.

    `Documents/ORV/ORV_Setting.ini` 파일을 작성하지 않음
    (`Documents/ORV/` 디렉토리도 부재). 예외 없이 False를 반환해야 한다.
    PRD AC4 매핑.
    """
    _patch_home(monkeypatch, tmp_path)

    importer = _make_importer()
    result = importer.is_development_mode()

    assert result is False
    assert isinstance(result, bool)


def test_returns_false_when_development_section_has_no_mode_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`[Development]` 섹션은 있으나 `mode` 키가 없는 환경에서 False를 반환한다.

    `NoOptionError` fallback 검증. PRD AC1(에러 차단) 보강 케이스.
    """
    _make_ini(tmp_path, "[Development]\nother=value\n")
    _patch_home(monkeypatch, tmp_path)

    importer = _make_importer()
    result = importer.is_development_mode()

    assert result is False
    assert isinstance(result, bool)
