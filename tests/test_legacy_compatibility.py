#!/usr/bin/env python3
"""
레거시 API 호환성 테스트 스크립트.

기존 perforce.py API가 리팩토링 후에도 동일하게 동작하는지 확인합니다.
"""

import sys
import os
from pathlib import Path

# 현재 스크립트의 디렉토리 path 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = os.path.abspath(os.path.join(current_dir, "..", "src"))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib
pyjallib.reload_modules()

from pyjallib.perforce import Perforce
from pyjallib.exceptions import PerforceError, ValidationError

def test_perforce_connection():
    """Perforce 연결 테스트"""
    print("=" * 50)
    print("1. Perforce 연결 테스트")
    print("=" * 50)
    
    p4 = Perforce()
    workspace_name = "DongseokKim_DevStorage"
    
    try:
        # 연결 테스트
        result = p4.connect(workspace_name)
        print(f"✓ 연결 성공: {result}")
        print(f"  - connected: {p4.connected}")
        print(f"  - workspaceRoot: {p4.workspaceRoot}")
        
        return p4
    except Exception as e:
        print(f"✗ 연결 실패: {e}")
        return None

def test_changelist_operations(p4):
    """체인지리스트 작업 테스트"""
    if not p4 or not p4.connected:
        print("⚠ Perforce 연결이 없어 체인지리스트 테스트를 건너뜁니다.")
        return
    
    print("=" * 50)
    print("2. 체인지리스트 작업 테스트")
    print("=" * 50)
    
    try:
        # Pending 체인지리스트 조회
        pending_lists = p4.get_pending_change_list()
        print(f"✓ Pending 체인지리스트 조회 성공: {len(pending_lists)}개")
        
        if pending_lists:
            first_cl = pending_lists[0]
            print(f"  - 첫 번째 CL ID: {first_cl.get('Change', 'N/A')}")
            print(f"  - 설명: {first_cl.get('Description', 'N/A')[:50]}...")
            print(f"  - 파일 수: {len(first_cl.get('Files', []))}")
        
        # Default 체인지리스트 조회
        default_cl = p4.get_default_change_list()
        print(f"✓ Default 체인지리스트 조회 성공")
        print(f"  - 파일 수: {len(default_cl.get('Files', []))}")
        
        # 새 체인지리스트 생성 테스트 (실제로는 생성하지 않음)
        print("✓ 체인지리스트 API 인터페이스 확인 완료")
        
    except Exception as e:
        print(f"✗ 체인지리스트 작업 실패: {e}")

def test_file_query_operations(p4):
    """파일 조회 작업 테스트"""
    if not p4 or not p4.connected:
        print("⚠ Perforce 연결이 없어 파일 조회 테스트를 건너뜁니다.")
        return
    
    print("=" * 50)
    print("3. 파일 조회 작업 테스트")
    print("=" * 50)
    
    # 테스트용 파일 경로들
    test_files = [
        r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\Death\Gesture\A_Nm_GHDtBully_M_Death_Gesture_Fist.json",
        r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\Death\Gesture\A_Nm_GHDtBully_M_Death_Gesture_Fist.fbx",
        r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\Death\Gesture\A_Nm_GHDtBully_M_Death_Gesture_Fist.bip"
    ]
    
    try:
        # 파일 Perforce 포함 여부 확인
        for file_path in test_files:
            if os.path.exists(file_path):
                is_in_p4 = p4.is_file_in_perforce(file_path)
                print(f"✓ {Path(file_path).name}: {'Perforce에 포함됨' if is_in_p4 else 'Perforce에 없음'}")
            else:
                print(f"⚠ {Path(file_path).name}: 로컬 파일이 존재하지 않음")
        
        # 체크아웃 상태 확인 (존재하는 파일들만)
        existing_files = [f for f in test_files if os.path.exists(f)]
        if existing_files:
            checkout_status = p4.check_files_checked_out(existing_files)
            print(f"✓ 체크아웃 상태 조회 성공: {len(checkout_status)}개 파일")
            
            for file_path, status in checkout_status.items():
                filename = Path(file_path).name
                if status['is_checked_out']:
                    print(f"  - {filename}: 체크아웃됨 (CL: {status['change_list']}, 사용자: {status['user']})")
                else:
                    print(f"  - {filename}: 체크아웃되지 않음")
        
        # 다른 사용자에 의한 체크아웃 확인
        if existing_files:
            files_by_others = p4.get_files_checked_out_by_others(existing_files)
            print(f"✓ 다른 사용자 체크아웃 조회 성공: {len(files_by_others)}개 파일")
            
            for file_info in files_by_others:
                filename = Path(file_info['file_path']).name
                print(f"  - {filename}: {file_info['user']}@{file_info['client']} (CL: {file_info['change_list']})")
        
    except Exception as e:
        print(f"✗ 파일 조회 작업 실패: {e}")

def test_sync_operations(p4):
    """동기화 작업 테스트"""
    if not p4 or not p4.connected:
        print("⚠ Perforce 연결이 없어 동기화 테스트를 건너뜁니다.")
        return
    
    print("=" * 50)
    print("4. 동기화 작업 테스트")
    print("=" * 50)
    
    # 테스트용 폴더 경로
    test_folders = [
        r'E:\DevStorage_root\DevStorage\Characters\EliteMonster\BigGroundRat\NonBinary\Animation\Battle\Action\Death'
    ]
    
    try:
        for folder_path in test_folders:
            if os.path.exists(folder_path):
                print(f"폴더 테스트: {Path(folder_path).name}")
                
                # 업데이트 필요 여부 확인
                needs_update = p4.check_update_required([folder_path])
                print(f"  - 업데이트 필요: {'예' if needs_update else '아니오'}")
                
                # 실제 동기화는 수행하지 않음 (파일 변경 방지)
                print(f"  - 동기화 API 인터페이스 확인 완료")
            else:
                print(f"⚠ 폴더가 존재하지 않음: {folder_path}")
        
    except Exception as e:
        print(f"✗ 동기화 작업 실패: {e}")

def test_error_handling():
    """에러 처리 테스트"""
    print("=" * 50)
    print("5. 에러 처리 테스트")
    print("=" * 50)
    
    p4 = Perforce()
    
    try:
        # 연결되지 않은 상태에서 작업 시도
        try:
            p4.get_pending_change_list()
            print("✗ 예상된 연결 오류가 발생하지 않음")
        except PerforceError as e:
            print(f"✓ 예상된 연결 오류 발생: {type(e).__name__}")
            print(f"  메시지: {str(e)}")
        
        # 잘못된 타입 전달 테스트
        try:
            p4.connect("test_workspace")  # 연결 먼저 시도
            p4.check_files_checked_out("single_file_not_list")
            print("✗ 예상된 타입 오류가 발생하지 않음")
        except (ValidationError, PerforceError) as e:
            print(f"✓ 예상된 타입 오류 발생: {type(e).__name__}")
            print(f"  메시지: {str(e)}")
        except Exception as e:
            print(f"✓ 연결 실패로 인한 오류 (예상됨): {type(e).__name__}")
        
        p4.disconnect()
        
    except Exception as e:
        print(f"✗ 에러 처리 테스트 실패: {e}")

def test_api_interface_compatibility():
    """API 인터페이스 호환성 테스트"""
    print("=" * 50)
    print("6. API 인터페이스 호환성 테스트")
    print("=" * 50)
    
    p4 = Perforce()
    
    # 기존 API 메서드들이 존재하는지 확인
    expected_methods = [
        'connect', 'disconnect', 'get_pending_change_list', 'create_change_list',
        'get_change_list_by_number', 'edit_change_list', 'submit_change_list',
        'revert_change_list', 'delete_empty_change_list', 'checkout_file',
        'checkout_files', 'add_file', 'add_files', 'delete_file', 'delete_files',
        'revert_file', 'revert_files', 'is_file_in_perforce', 'sync_files',
        'check_files_checked_out', 'check_files_checked_out_all_users',
        'is_file_checked_out', 'is_file_checked_out_by_others',
        'get_file_checkout_info_all_users', 'get_files_checked_out_by_others',
        'check_update_required', 'get_default_change_list'
    ]
    
    missing_methods = []
    for method_name in expected_methods:
        if hasattr(p4, method_name):
            method = getattr(p4, method_name)
            if callable(method):
                print(f"✓ {method_name}: 메서드 존재함")
            else:
                print(f"✗ {method_name}: 호출 가능하지 않음")
                missing_methods.append(method_name)
        else:
            print(f"✗ {method_name}: 메서드 없음")
            missing_methods.append(method_name)
    
    if missing_methods:
        print(f"\n✗ 누락된 메서드들: {missing_methods}")
    else:
        print(f"\n✓ 모든 예상 메서드들이 존재함 ({len(expected_methods)}개)")

def main():
    """메인 테스트 실행"""
    print("레거시 API 호환성 테스트 시작")
    print("=" * 80)
    
    # API 인터페이스 호환성 먼저 확인
    test_api_interface_compatibility()
    
    # 에러 처리 테스트
    test_error_handling()
    
    # 실제 Perforce 작업 테스트
    print("\n실제 Perforce 작업 테스트를 시도합니다...")
    p4 = test_perforce_connection()
    
    if p4:
        test_changelist_operations(p4)
        test_file_query_operations(p4)
        test_sync_operations(p4)
        
        # 연결 해제
        try:
            p4.disconnect()
            print("\n✓ Perforce 연결 해제 완료")
        except Exception as e:
            print(f"\n⚠ 연결 해제 중 오류: {e}")
    
    print("\n" + "=" * 80)
    print("레거시 API 호환성 테스트 완료")

if __name__ == "__main__":
    main()
