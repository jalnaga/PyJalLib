#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dependent 모듈 테스트 스크립트
3DS Max Python 환경에서 실행

사용법:
1. 3DS Max에서 Listener 열기 (F11)
2. 이 스크립트를 실행하거나 아래 코드를 직접 붙여넣기

테스트 전 필수 조건:
- 씬에 스킨이 적용된 메시가 있어야 함
- 본/헬퍼 계층 구조가 있어야 함
- (선택) AddOn 레이어가 있으면 해당 테스트도 확인 가능
"""

from pymxs import runtime as rt


def run_all_tests():
    """모든 테스트 케이스 실행"""
    print("=" * 60)
    print("Dependent 모듈 테스트 시작")
    print("=" * 60)
    
    # Header 초기화
    from pyjallib.max.header import get_pyjallibmaxheader
    jal = get_pyjallibmaxheader()
    
    print(f"\n[INFO] jal.dependent 초기화 확인: {jal.dependent}")
    print(f"[INFO] layerService 주입 확인: {jal.dependent.layerService}")
    
    # 테스트 1: 빈 선택 테스트
    test_empty_selection(jal)
    
    # 테스트 2: get_all_dependencies 테스트
    test_get_all_dependencies(jal)
    
    # 테스트 3: get_dependents 테스트
    test_get_dependents(jal)
    
    # 테스트 4: get_all_related_to_export 테스트
    test_get_all_related_to_export(jal)
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


def test_empty_selection(jal):
    """빈 선택에서 오류 없이 빈 결과 반환하는지 테스트"""
    print("\n" + "-" * 40)
    print("[TEST 1] 빈 선택 테스트")
    print("-" * 40)
    
    try:
        # 빈 배열로 테스트
        deps, visited = jal.dependent.get_all_dependencies([])
        print(f"  get_all_dependencies([]): {len(deps)}개 결과, visited={len(visited)}")
        assert len(deps) == 0, "빈 입력에서 빈 결과여야 함"
        
        dependents = jal.dependent.get_dependents([])
        print(f"  get_dependents([]): {len(dependents)}개 결과")
        assert len(dependents) == 0, "빈 입력에서 빈 결과여야 함"
        
        result = jal.dependent.get_all_related_to_export([])
        print(f"  get_all_related_to_export([]): {len(result)}개 결과")
        assert len(result) == 0, "빈 입력에서 빈 결과여야 함"
        
        print("  [PASS] 빈 선택 테스트 통과")
    except Exception as e:
        print(f"  [FAIL] 오류 발생: {e}")


def test_get_all_dependencies(jal):
    """get_all_dependencies 메서드 테스트"""
    print("\n" + "-" * 40)
    print("[TEST 2] get_all_dependencies 테스트")
    print("-" * 40)
    
    sel = list(rt.getCurrentSelection())
    
    if not sel:
        print("  [SKIP] 오브젝트를 선택한 후 테스트를 다시 실행하세요.")
        print("  사용법: 스킨이 적용된 메시를 선택 후 test_get_all_dependencies(jal) 실행")
        return
    
    try:
        print(f"  입력: {len(sel)}개 오브젝트 선택됨")
        for obj in sel[:5]:  # 최대 5개만 출력
            print(f"    - {obj.name}")
        if len(sel) > 5:
            print(f"    ... 외 {len(sel) - 5}개")
        
        deps, visited = jal.dependent.get_all_dependencies(sel)
        
        print(f"\n  결과: {len(deps)}개 dependency 노드 발견")
        print(f"  방문한 노드: {len(visited)}개")
        
        # Biped 제외 확인
        biped_count = 0
        for obj in deps:
            if rt.classOf(obj) == rt.Biped_Object:
                biped_count += 1
        
        print(f"\n  Biped 오브젝트 포함 수: {biped_count}")
        if biped_count == 0:
            print("  [PASS] Biped 오브젝트가 결과에서 제외됨")
        else:
            print("  [FAIL] Biped 오브젝트가 결과에 포함됨")
        
        # 결과 출력 (최대 10개)
        print("\n  발견된 노드들 (최대 10개):")
        for obj in deps[:10]:
            objClass = rt.classOf(obj)
            print(f"    - {obj.name} ({objClass})")
        if len(deps) > 10:
            print(f"    ... 외 {len(deps) - 10}개")
            
    except Exception as e:
        print(f"  [FAIL] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_get_dependents(jal):
    """get_dependents 메서드 테스트"""
    print("\n" + "-" * 40)
    print("[TEST 3] get_dependents 테스트")
    print("-" * 40)
    
    sel = list(rt.getCurrentSelection())
    
    if not sel:
        print("  [SKIP] 오브젝트를 선택한 후 테스트를 다시 실행하세요.")
        print("  사용법: 부모 노드를 선택 후 test_get_dependents(jal) 실행")
        return
    
    try:
        print(f"  입력: {len(sel)}개 오브젝트 선택됨")
        
        dependents = jal.dependent.get_dependents(sel)
        
        print(f"\n  결과: {len(dependents)}개 dependent 노드 발견")
        print(f"  (원본 {len(sel)}개 포함)")
        
        # Biped 제외 확인
        biped_count = 0
        for obj in dependents:
            if rt.classOf(obj) == rt.Biped_Object:
                biped_count += 1
        
        print(f"\n  Biped 오브젝트 포함 수: {biped_count}")
        if biped_count == 0:
            print("  [PASS] Biped 오브젝트가 결과에서 제외됨")
        else:
            print("  [FAIL] Biped 오브젝트가 결과에 포함됨")
        
        # 결과 출력 (최대 10개)
        print("\n  발견된 노드들 (최대 10개):")
        for obj in dependents[:10]:
            objClass = rt.classOf(obj)
            print(f"    - {obj.name} ({objClass})")
        if len(dependents) > 10:
            print(f"    ... 외 {len(dependents) - 10}개")
            
    except Exception as e:
        print(f"  [FAIL] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_get_all_related_to_export(jal):
    """get_all_related_to_export 메서드 테스트"""
    print("\n" + "-" * 40)
    print("[TEST 4] get_all_related_to_export 테스트")
    print("-" * 40)
    
    sel = list(rt.getCurrentSelection())
    
    if not sel:
        print("  [SKIP] 오브젝트를 선택한 후 테스트를 다시 실행하세요.")
        print("  사용법: 캐릭터 메시를 선택 후 test_get_all_related_to_export(jal) 실행")
        return
    
    try:
        print(f"  입력: {len(sel)}개 오브젝트 선택됨")
        
        result = jal.dependent.get_all_related_to_export(sel)
        
        print(f"\n  결과: {len(result)}개 익스포트 관련 노드 발견")
        
        # 선택 확인
        newSel = list(rt.getCurrentSelection())
        print(f"  현재 선택: {len(newSel)}개")
        
        # Biped 제외 확인
        biped_count = 0
        for obj in result:
            if rt.classOf(obj) == rt.Biped_Object:
                biped_count += 1
        
        print(f"\n  Biped 오브젝트 포함 수: {biped_count}")
        if biped_count == 0:
            print("  [PASS] Biped 오브젝트가 결과에서 제외됨")
        else:
            print("  [FAIL] Biped 오브젝트가 결과에 포함됨")
        
        # Helper 수 카운트
        helper_count = 0
        for obj in result:
            if rt.superClassOf(obj) == rt.Helper:
                helper_count += 1
        print(f"  Helper 오브젝트 수: {helper_count}")
        
        # AddOn 레이어 확인
        addon_layers = jal.layer.get_layer_by_namepattern("*AddOn*")
        print(f"\n  AddOn 레이어 발견: {len(addon_layers)}개")
        for layerName in addon_layers:
            print(f"    - {layerName}")
        
        # 결과 출력 (최대 15개)
        print("\n  발견된 노드들 (최대 15개):")
        for obj in result[:15]:
            objClass = rt.classOf(obj)
            superClass = rt.superClassOf(obj)
            print(f"    - {obj.name} ({objClass}, {superClass})")
        if len(result) > 15:
            print(f"    ... 외 {len(result) - 15}개")
            
    except Exception as e:
        print(f"  [FAIL] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_circular_reference(jal):
    """순환 참조 테스트 (무한 루프 방지 확인)"""
    print("\n" + "-" * 40)
    print("[TEST 5] 순환 참조 테스트")
    print("-" * 40)
    
    sel = list(rt.getCurrentSelection())
    
    if not sel:
        print("  [SKIP] 오브젝트를 선택한 후 테스트를 다시 실행하세요.")
        return
    
    try:
        print(f"  입력: {len(sel)}개 오브젝트")
        print("  순환 참조 테스트 시작 (무한 루프 시 타임아웃)...")
        
        # 타임아웃 없이 실행 (무한 루프 발생 시 수동 중단 필요)
        deps, visited = jal.dependent.get_all_dependencies(sel)
        
        print(f"  결과: {len(deps)}개 노드 발견")
        print(f"  방문한 노드: {len(visited)}개")
        print("  [PASS] 순환 참조 시 무한 루프 없이 처리됨")
        
    except Exception as e:
        print(f"  [FAIL] 오류 발생: {e}")


# 개별 테스트 함수들 (3DS Max Listener에서 직접 호출 가능)
def quick_test():
    """빠른 테스트 - 선택된 오브젝트로 모든 기능 테스트"""
    from pyjallib.max.header import get_pyjallibmaxheader
    jal = get_pyjallibmaxheader()
    
    sel = list(rt.getCurrentSelection())
    if not sel:
        print("오브젝트를 선택한 후 다시 실행하세요.")
        return
    
    print(f"\n선택: {len(sel)}개 오브젝트")
    
    # Dependencies
    deps, _ = jal.dependent.get_all_dependencies(sel)
    print(f"Dependencies: {len(deps)}개")
    
    # Dependents
    dependents = jal.dependent.get_dependents(sel)
    print(f"Dependents: {len(dependents)}개")
    
    # All Related
    result = jal.dependent.get_all_related_to_export(sel)
    print(f"Export Related: {len(result)}개")
    print("완료 - 선택이 변경되었습니다.")


# 스크립트 직접 실행 시
if __name__ == "__main__":
    run_all_tests()
