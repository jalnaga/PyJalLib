# -*- coding: utf-8 -*-
"""_FuzzyFilterProxyModel 클래스 단위 테스트."""

import pytest
from PySide2 import QtWidgets, QtGui, QtCore
from pyjallib.max.ui.fuzzySearchComboBox import _FuzzyFilterProxyModel


@pytest.fixture(scope="session")
def qapp():
    """세션 범위 QApplication 인스턴스. 이미 존재하면 재사용한다."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def model_with_items(qapp):
    """QStandardItemModel + _FuzzyFilterProxyModel 세트를 반환한다."""
    sourceModel = QtGui.QStandardItemModel()
    for name in ["KimDokja", "YooJoonghyuk", "HanSooyoung"]:
        sourceModel.appendRow(QtGui.QStandardItem(name))

    proxyModel = _FuzzyFilterProxyModel()
    proxyModel.setSourceModel(sourceModel)

    return sourceModel, proxyModel


def _visible_texts(inProxyModel: _FuzzyFilterProxyModel) -> list:
    """프록시 모델에서 현재 보이는 항목 텍스트 목록을 반환한다."""
    texts = []
    for row in range(inProxyModel.rowCount()):
        index = inProxyModel.index(row, 0)
        texts.append(inProxyModel.data(index, QtCore.Qt.DisplayRole))
    return texts


def test_filter_kd_only_kimdokja(model_with_items):
    """패턴 'kd' 설정 시 'KimDokja'만 통과한다."""
    sourceModel, proxyModel = model_with_items
    proxyModel.set_filter_pattern("kd")

    texts = _visible_texts(proxyModel)
    assert "KimDokja" in texts
    assert "YooJoonghyuk" not in texts
    assert "HanSooyoung" not in texts


def test_empty_pattern_passes_all(model_with_items):
    """빈 패턴 설정 시 전체 항목이 통과한다."""
    sourceModel, proxyModel = model_with_items
    proxyModel.set_filter_pattern("")

    texts = _visible_texts(proxyModel)
    assert len(texts) == 3
    assert "KimDokja" in texts
    assert "YooJoonghyuk" in texts
    assert "HanSooyoung" in texts


def test_filter_oo_passes_two_items(model_with_items):
    """패턴 'oo' 설정 시 'YooJoonghyuk'과 'HanSooyoung'이 통과한다."""
    sourceModel, proxyModel = model_with_items
    proxyModel.set_filter_pattern("oo")

    texts = _visible_texts(proxyModel)
    assert "YooJoonghyuk" in texts
    assert "HanSooyoung" in texts
    assert "KimDokja" not in texts


def test_filter_oo_sorted_by_score(model_with_items):
    """패턴 'oo' 설정 시 결과가 점수 내림차순으로 정렬된다."""
    sourceModel, proxyModel = model_with_items
    proxyModel.set_filter_pattern("oo")

    texts = _visible_texts(proxyModel)
    # 결과가 2개이며 정렬되어 있어야 한다
    assert len(texts) == 2
    # YooJoonghyuk: 'oo'가 인덱스 1,2 (연속 매칭 + 단어 시작 보너스)
    # HanSooyoung: 'oo'가 인덱스 4,5 (연속 매칭)
    # 두 항목 모두 통과하고 점수 높은 쪽이 앞에 위치해야 한다
    from pyjallib.max.ui.fuzzySearchComboBox import _fuzzy_score
    score_yoo = _fuzzy_score("oo", "YooJoonghyuk")
    score_han = _fuzzy_score("oo", "HanSooyoung")

    if score_yoo >= score_han:
        assert texts[0] == "YooJoonghyuk"
    else:
        assert texts[0] == "HanSooyoung"
