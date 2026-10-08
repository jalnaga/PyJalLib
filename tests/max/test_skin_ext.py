#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Skin 확장 메서드 테스트 - 3ds Max 환경에서 실행 (Type C).

``get_selected_vertices`` / ``select_vertices`` / ``set_vertex_weights`` / ``get_bone_nodes`` /
``add_bones`` / ``remove_bone`` / ``duplicate_skin`` / ``mirror_weights`` / ``load_skin`` 배치(``insert_before``)를 검증한다.

**빈 슬롯 픽스처.** 리거가 본을 붙였다 뗀 프로덕션 Skin에는 빈 슬롯이 있고(2026-10-06
SK_TREX 실기 자산에서도 확인), 그때 ``addBone``이 본 ID를 민다(``max/skin_bone_id.md`` §2).
갓 만든 Skin에는 그 조건이 없으므로 앞(ID 1)·중간 본을 ``removeBone``해 빈 슬롯을 만든 뒤
모든 TC를 그 Skin에서 돈다. TC03이 "조건이 실제로 만들어졌는가"(새 본 ID != 끝)를 먼저 단정한다.

판정은 **노드 핸들/이름 기준 가중치 항등식**이다(본 ID는 밀리므로 기준이 될 수 없다).
검증 읽기 전에는 항상 ``activate_skin`` + ``completeRedraw``(쓰기 직후 재조회 0 함정).

합성 씬(박스 본):

    root(0,0,0) > spine(0,0,10) > Arm_L(-10,0,10) > Hand_L(-20,0,10)
                                > Arm_R( 10,0,10) > Hand_R( 20,0,10)
    tmp_a, tmp_b, extra  독립
    Body: Box width 40(x -20..20, 8 세그먼트) - x=0 기준 좌우 대칭 버텍스 36개

기대 TC 수: 17 (TC00~TC16)

실행:
    uv run python tests/run_max_tests.py test_skin_ext.py
"""

import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from _bootstrap import assert_loaded_from_checkout, bootstrap_pyjallib

bootstrap_pyjallib()

from pymxs import runtime as rt

import pyjallib
from pyjallib.max import skinWeightMath as swm
from pyjallib.max.skin import Skin
from pyjallib.testKit import TestReporter

LOG_DIR = Path(__file__).parent.parent / "logs"
reporter = TestReporter("SkinExt", LOG_DIR)
TOL = 1e-5

skin = Skin()


def _bone(inName, inPos, inParent=None):
    node = rt.Box(name=inName, width=1.0, length=1.0, height=2.0)
    node.pos = rt.Point3(*inPos)
    if inParent is not None:
        node.parent = inParent
    return node


def rule_weights(inX: float) -> Dict[str, float]:
    """x 위치로 정하는 좌우 대칭 가중치 규칙."""
    if inX < -12:
        return {"Hand_L": 0.7, "Arm_L": 0.3}
    if inX < -2:
        return {"Arm_L": 0.8, "spine": 0.2}
    if inX <= 2:
        return {"spine": 1.0}
    if inX <= 12:
        return {"Arm_R": 0.8, "spine": 0.2}
    return {"Hand_R": 0.7, "Arm_R": 0.3}


def build_scene() -> Dict[str, Any]:
    """빈 슬롯 2개가 있는 Skin 씬을 짓는다."""
    rt.resetMaxFile(rt.Name("noPrompt"))
    n: Dict[str, Any] = {}
    n["root"] = _bone("root", (0, 0, 0))
    n["spine"] = _bone("spine", (0, 0, 10), n["root"])
    n["Arm_L"] = _bone("Arm_L", (-10, 0, 10), n["spine"])
    n["Hand_L"] = _bone("Hand_L", (-20, 0, 10), n["Arm_L"])
    n["Arm_R"] = _bone("Arm_R", (10, 0, 10), n["spine"])
    n["Hand_R"] = _bone("Hand_R", (20, 0, 10), n["Arm_R"])
    n["tmp_a"] = _bone("tmp_a", (0, 20, 0))
    n["tmp_b"] = _bone("tmp_b", (0, 25, 0))
    n["extra"] = _bone("extra", (0, -20, 0))

    body = rt.Box(name="Body", width=40.0, length=4.0, height=4.0, widthsegs=8, lengthsegs=1, heightsegs=1)
    body.pos = rt.Point3(0, 0, 8)
    sk = rt.Skin()
    rt.addModifier(body, sk)
    skin.activate_skin(body, sk)
    for name in ("tmp_a", "spine", "tmp_b", "Arm_L", "Arm_R", "Hand_L", "Hand_R"):
        rt.skinOps.addBone(sk, n[name], 1)
    sk.enableDQ = False
    rt.completeRedraw()
    write_rule(body, sk, list(range(1, int(rt.skinOps.GetNumberVertices(sk)) + 1)))
    # 앞(ID 1 tmp_a) 제거 -> tmp_b가 ID 2가 된다 -> 중간(ID 2) 제거: 빈 슬롯 2개
    rt.skinOps.removeBone(sk, 1)
    rt.skinOps.removeBone(sk, 2)
    skin.activate_skin(body, sk)
    rt.completeRedraw()
    n["Body"], n["skin"] = body, sk
    return n


def positions(inNode) -> List[tuple]:
    mesh = rt.snapshotAsMesh(inNode)
    return [
        (float(p.x), float(p.y), float(p.z))
        for p in (rt.meshop.getVert(mesh, v) for v in range(1, int(rt.getNumVerts(mesh)) + 1))
    ]


def id_by_name(inSkinMod) -> Dict[str, int]:
    return {str(e["name"]): bid for bid, e in skin.get_bone_table(inSkinMod).items()}


def write_rule(inNode, inSkinMod, inVerts) -> None:
    ids = id_by_name(inSkinMod)
    pos = positions(inNode)
    skin.set_vertex_weights(
        inSkinMod,
        {
            v: ([ids[k] for k in rule_weights(pos[v - 1][0])], list(rule_weights(pos[v - 1][0]).values()))
            for v in inVerts
        },
    )


def read_by_name(inNode, inSkinMod) -> Dict[int, Dict[str, float]]:
    """``{버텍스: {본 이름: w}}`` - 활성화 + redraw 후 읽는다."""
    skin.activate_skin(inNode, inSkinMod)
    rt.completeRedraw()
    table = skin.get_bone_table(inSkinMod)
    out: Dict[int, Dict[str, float]] = {}
    for v, entries in skin.get_vertex_weights(inSkinMod).items():
        d: Dict[str, float] = {}
        for bid, w in entries:
            if w > 0:
                name = str(table[bid]["name"])
                d[name] = d.get(name, 0.0) + w
        out[v] = d
    return out


def same(inA: Dict[str, float], inB: Dict[str, float]) -> bool:
    keys = set(inA) | set(inB)
    return all(abs(inA.get(k, 0.0) - inB.get(k, 0.0)) <= TOL for k in keys)


def run(inName: str, inFn) -> None:
    try:
        ok, detail = inFn()
        reporter.assert_test(bool(ok), inName, str(detail)[:600])
    except Exception as e:  # noqa: BLE001
        reporter.error(inName, f"{e}\n{traceback.format_exc()[-1500:]}")


# ---------------------------------------------------------------------------

run(
    "TC00 로드 출처가 이 체크아웃 + skinWeightMath 존재",
    lambda: (
        assert_loaded_from_checkout(pyjallib) and hasattr(swm, "mix_weights"),
        f"pyjallib.__file__={pyjallib.__file__}",
    ),
)


def tc01():
    n = build_scene()
    sk = n["skin"]
    names = sorted(id_by_name(sk))
    w = read_by_name(n["Body"], sk)
    sums = [sum(d.values()) for d in w.values()]
    ok = names == ["Arm_L", "Arm_R", "Hand_L", "Hand_R", "spine"] and len(w) == 36 and all(abs(s - 1) < TOL for s in sums)
    return ok, f"bones={names} verts={len(w)}"


run("TC01 픽스처: 본 5개(빈 슬롯 2개 생성 후) + 버텍스 36개 + 합 1", tc01)


def tc02():
    n = build_scene()
    sk = n["skin"]
    skin.activate_skin(n["Body"], sk)
    skin.select_vertices(sk, [9, 1, 5])
    a = skin.get_selected_vertices(sk)
    skin.select_vertices(sk, [])
    b = skin.get_selected_vertices(sk)
    return a == [1, 5, 9] and b == [], f"a={a} b={b}"


run("TC02 select_vertices / get_selected_vertices 왕복", tc02)


def tc03():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    before = read_by_name(body, sk)
    countBefore = int(rt.skinOps.GetNumberBones(sk))
    result = skin.add_bones(body, sk, [n["extra"]])
    newId = result[int(rt.getHandleByAnim(n["extra"]))]
    nodeAtId = str(rt.skinOps.GetBoneNode(sk, newId).name)
    after = read_by_name(body, sk)
    preserved = all(same(before[v], after[v]) for v in before)
    ok = newId != countBefore + 1 and nodeAtId == "extra" and preserved
    return ok, f"newId={newId} (끝이면 {countBefore + 1}) nodeAtId={nodeAtId} preserved={preserved}"


run("TC03 add_bones: 빈 슬롯 조건 실재(ID != 끝) + 핸들 기준 ID 정확 + 기존 가중치 보존", tc03)


def tc04():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    ids = id_by_name(sk)
    skin.activate_skin(body, sk)
    skin.set_vertex_weights(sk, {1: ([ids["spine"]], [0.2])})
    got = read_by_name(body, sk)[1]
    return same(got, {"spine": 1.0}), f"got={got}"


run("TC04 set_vertex_weights 단일 본 0.2 -> 정규화 1.0 (Max 원시 쓰기는 0.0)", tc04)


def tc05():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    ids = id_by_name(sk)
    skin.activate_skin(body, sk)
    skin.set_vertex_weights(sk, {2: ([ids["spine"], ids["Arm_L"], ids["spine"]], [0.1, 0.6, 0.1])})
    got = read_by_name(body, sk)[2]
    return same(got, {"spine": 0.25, "Arm_L": 0.75}), f"got={got}"


run("TC05 set_vertex_weights 다중 본 + 같은 본 중복 합산 + 정규화", tc05)


def tc06():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    before = read_by_name(body, sk)
    skin.activate_skin(body, sk)
    skipped = skin.set_vertex_weights(sk, {3: ([], [])})
    written = skin.set_vertex_weights(sk, {4: ([], [])}, inWriteEmpty=True)
    after = read_by_name(body, sk)
    ok = skipped == [] and written == [4] and same(after[3], before[3]) and after[4] == {}
    return ok, f"skipped={skipped} written={written} v3={after[3]} v4={after[4]}"


run("TC06 set_vertex_weights 빈 항목: 기본 건너뜀 / inWriteEmpty=True면 무웨이트", tc06)


def tc07():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    skin.activate_skin(body, sk)
    nodes = [str(x.name) for x in skin.get_bone_nodes(sk)]
    table = skin.get_bone_table(sk)
    expected = [str(table[b]["name"]) for b in sorted(table)]
    return nodes == expected, f"nodes={nodes} table={expected}"


run("TC07 get_bone_nodes는 본 ID 순서(대조표와 일치)", tc07)


def tc08():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    skin.add_bones(body, sk, [n["extra"]])  # ID를 한 번 더 민 상태에서 제거
    before = read_by_name(body, sk)
    report = skin.remove_bone(body, sk, int(rt.getHandleByAnim(n["Hand_L"])))
    after = read_by_name(body, sk)
    names = set(id_by_name(sk))
    identity = all(
        abs(after[v].get("Arm_L", 0.0) - (before[v].get("Arm_L", 0.0) + before[v].get("Hand_L", 0.0))) <= TOL
        and after[v].get("Hand_L", 0.0) == 0.0
        and abs(sum(after[v].values()) - 1.0) <= TOL
        for v in before
    )
    touched = sum(1 for v in before if before[v].get("Hand_L", 0.0) > 0)
    ok = report["transferredTo"] == "Arm_L" and "Hand_L" not in names and identity and touched > 0 and report["weightlessVerts"] == []
    return ok, f"report.transferredTo={report['transferredTo']} touched={touched} identity={identity} names={sorted(names)}"


run("TC08 remove_bone 부모 이전: Arm_L = Arm_L + Hand_L, Hand_L 제거, 합 1 (빈 슬롯 Skin)", tc08)


def tc09():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    ids = skin.add_bones(body, sk, [n["extra"]])
    extraId = ids[int(rt.getHandleByAnim(n["extra"]))]
    skin.activate_skin(body, sk)
    skin.set_vertex_weights(sk, {7: ([extraId], [1.0]), 8: ([extraId, id_by_name(sk)["spine"]], [0.5, 0.5])})
    report = skin.remove_bone(body, sk, int(rt.getHandleByAnim(n["extra"])))
    after = read_by_name(body, sk)
    ok = report["transferredTo"] is None and report["weightlessVerts"] == [7] and same(after[8], {"spine": 1.0})
    return ok, f"report={ {k: report[k] for k in ('removed', 'transferredTo', 'weightlessVerts')} } v8={after[8]}"


run("TC09 remove_bone 부모 없음: 제거 + 무웨이트 버텍스 보고(v7), 공유 버텍스 재정규화", tc09)


def tc10():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    source = read_by_name(body, sk)
    copy = skin.duplicate_skin(body, sk, inName="Skin_Backup")
    skins = [m for m in body.modifiers if rt.classOf(m) == rt.Skin]
    current = rt.modPanel.getCurrentObject()
    copied = read_by_name(body, copy)
    match = all(same(source[v], copied[v]) for v in source)
    ok = len(skins) == 2 and match and not bool(copy.enabled) and str(current.name) == str(sk.name) and str(copy.name) == "Skin_Backup"
    return ok, f"skins={len(skins)} match={match} copyEnabled={bool(copy.enabled)} current={current.name}"


run("TC10 duplicate_skin: 핸들 기준 동일 + 비활성 + 원본이 현재 객체", tc10)


def _mirror_setup():
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    pos = positions(body)
    vmap0 = swm.mirror_vertex_map_by_position(pos)
    vmap = {v + 1: m + 1 for v, m in enumerate(vmap0)}
    ids = id_by_name(sk)
    right = [v for v in range(1, len(pos) + 1) if pos[v - 1][0] > 2]
    skin.activate_skin(body, sk)
    skin.set_vertex_weights(sk, {v: ([ids["spine"]], [1.0]) for v in right})
    return n, sk, body, pos, vmap, right


def tc11():
    n, sk, body, pos, vmap, right = _mirror_setup()
    left = [v for v in range(1, len(pos) + 1) if pos[v - 1][0] < -2]
    written = skin.mirror_weights(body, sk, vmap, left)
    after = read_by_name(body, sk)
    ok = sorted(written) == sorted(right) and all(same(after[v], rule_weights(pos[v - 1][0])) for v in after)
    return ok, f"written={len(written)} right={len(right)}"


run("TC11 mirror_weights 왼쪽 -> 오른쪽: 본 이름 대칭 + 위치 맵으로 규칙 복원", tc11)


def tc12():
    n, sk, body, pos, vmap, right = _mirror_setup()
    allVerts = list(range(1, len(pos) + 1))
    skin.mirror_weights(body, sk, vmap, allVerts)
    after = read_by_name(body, sk)
    # 박스 버텍스는 행마다 x가 증가 - 짝 중 인덱스가 작은 쪽이 왼쪽이다.
    # 원본 동작(뒤에서 앞을 다시 읽음)이면 왼쪽이 오른쪽(spine)을 받고, 오른쪽은 바뀐 왼쪽을
    # 다시 받아 전부 spine. 맞바꿈(스냅샷 읽기)이면 오른쪽이 규칙값이 된다.
    allSpine = all(same(after[v], {"spine": 1.0}) for v in after)
    return allSpine, f"sample v1={after[1]} v9={after[9]}"


run("TC12 mirror_weights 양쪽 선택: L/R 맞바꿈 없음(원본 순차 동작)", tc12)


def tc13():
    """기존 API 회귀 표본: transfert_skin_data 래퍼가 여전히 이전한다."""
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    before = read_by_name(body, sk)
    skin.transfert_skin_data(body, n["Hand_R"], n["Arm_R"], list(range(1, 37)))
    after = read_by_name(body, sk)
    ok = all(
        abs(after[v].get("Arm_R", 0.0) - (before[v].get("Arm_R", 0.0) + before[v].get("Hand_R", 0.0))) <= TOL
        for v in before
    )
    return ok, "transfert_skin_data 보존 항등식"


run("TC13 기존 transfert_skin_data 회귀(빈 슬롯 Skin)", tc13)


# ---------------------------------------------------------------------------
# load_skin 배치(insert_before) - 2026-10-08 SkinKitPy Load 결함: keep_skin=True가 배치까지
# before:1로 묶어 "보존 + 기존 Skin 위" 배치를 표현할 수 없었다.

SKIN_TMP_DIR = LOG_DIR / "_skin_ext_tmp"


def _saved_scene(inStem: str, inBendOnTop: bool = False):
    """픽스처를 ``.skin``으로 저장하고 ``(씬, 원본 가중치, 파일 경로)``를 돌려준다."""
    n = build_scene()
    sk, body = n["skin"], n["Body"]
    source = read_by_name(body, sk)
    SKIN_TMP_DIR.mkdir(parents=True, exist_ok=True)
    path = SKIN_TMP_DIR / f"{inStem}.skin"
    if path.exists():
        path.unlink()
    skin.activate_skin(body, sk)
    if skin.save_skin(body, str(path)) is None:
        raise RuntimeError(f"save_skin 실패: {path}")
    if inBendOnTop:
        rt.addModifier(body, rt.Bend())
    return n, source, path


def stack_names(inNode) -> List[str]:
    """모디파이어 이름(스택 위에서 아래 순)."""
    return [str(m.name) for m in inNode.modifiers]


def tc14():
    """미지정이면 현행 배치: keep_skin=True는 맨 위 아래(before:1), False는 기존 삭제 후 맨 위."""
    n, source, path = _saved_scene("Body_keep")
    body = n["Body"]
    skin.load_skin(body, str(path), keep_skin=True)
    keepStack = stack_names(body)
    n2, source2, path2 = _saved_scene("Body_replace")
    body2 = n2["Body"]
    skin.load_skin(body2, str(path2), keep_skin=False)
    replaceStack = stack_names(body2)
    loaded = read_by_name(body2, body2.modifiers[0])
    match = all(same(source2[v], loaded[v]) for v in source2)
    ok = keepStack == ["Skin", "Skin_Body_keep"] and replaceStack == ["Skin"] and match
    return ok, f"keep={keepStack} replace={replaceStack} match={match}"


run("TC14 load_skin insert_before 미지정: keep_skin True/False 현행 배치 유지", tc14)


def tc15():
    """keep_skin=True + insert_before=0: 기존 Skin을 보존한 채 새 Skin이 맨 위."""
    n, source, path = _saved_scene("Body_top")
    body, old = n["Body"], n["skin"]
    skin.load_skin(body, str(path), keep_skin=True, insert_before=0)
    stack = stack_names(body)
    new = body.modifiers[0]
    loaded = read_by_name(body, new)
    match = all(same(source[v], loaded[v]) for v in source)
    ok = stack == ["Skin_Body_top", "Skin"] and body.modifiers[1] == old and match
    return ok, f"stack={stack} match={match}"


run("TC15 load_skin keep_skin + insert_before=0: 새 Skin 맨 위, 기존 Skin 보존", tc15)


def tc16():
    """Skin 위에 Bend가 있을 때 insert_before=1: Bend / 새 Skin / 기존 Skin."""
    n, source, path = _saved_scene("Body_bend", inBendOnTop=True)
    body, old = n["Body"], n["skin"]
    skin.load_skin(body, str(path), keep_skin=True, insert_before=1)
    stack = stack_names(body)
    loaded = read_by_name(body, body.modifiers[1])
    match = all(same(source[v], loaded[v]) for v in source)
    ok = stack == ["Bend", "Skin_Body_bend", "Skin"] and body.modifiers[2] == old and match
    return ok, f"stack={stack} match={match}"


run("TC16 load_skin insert_before=1(Skin 위 Bend): Bend / 새 Skin / 기존 Skin", tc16)

try:
    rt.setSaveRequired(False)
except Exception:  # noqa: BLE001
    pass
reporter.summary()
reporter.close()
