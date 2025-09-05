#!/usr/bin/env python3
"""
perforceCore 패키지 테스트 스크립트.

기존 레거시 API와 신규 코어 API의 동작을 확인합니다.
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

# 기존 레거시 API 테스트
from pyjallib.perforce import Perforce

# 신규 코어 API 테스트
from pyjallib.perforceCore import P4Adapter, PerforceService, ChangeListInfo, FileInfo

def test_basic_imports():
    """기본 임포트가 제대로 동작하는지 확인"""
    print("=" * 50)
    print("1. 기본 임포트 테스트")
    print("=" * 50)
    
    print("✓ 레거시 Perforce 클래스 임포트 성공")
    print("✓ P4Adapter 임포트 성공")
    print("✓ PerforceService 임포트 성공")
    print("✓ DTO 클래스들 임포트 성공")
    print()

def test_legacy_initialization():
    """레거시 API 초기화 테스트"""
    print("=" * 50)
    print("2. 레거시 API 초기화 테스트")
    print("=" * 50)
    
    try:
        legacy_p4 = Perforce()
        print("✓ 레거시 Perforce 클래스 초기화 성공")
        print(f"  - connected: {legacy_p4.connected}")
        print(f"  - workspaceRoot: {legacy_p4.workspaceRoot}")
        print(f"  - p4 handle: {type(legacy_p4.p4).__name__}")
        print(f"  - _adapter: {type(legacy_p4._adapter).__name__}")
        print(f"  - _service: {type(legacy_p4._service).__name__}")
        return legacy_p4
    except Exception as e:
        print(f"✗ 레거시 Perforce 초기화 실패: {e}")
        return None

def test_core_initialization():
    """신규 코어 API 초기화 테스트"""
    print("=" * 50)
    print("3. 신규 코어 API 초기화 테스트")
    print("=" * 50)
    
    try:
        adapter = P4Adapter()
        print("✓ P4Adapter 초기화 성공")
        print(f"  - connected: {adapter.connected}")
        print(f"  - workspaceRoot: {adapter.workspaceRoot}")
        print(f"  - p4: {type(adapter.p4).__name__}")
        
        service = PerforceService(adapter, in_auto_revert_unchanged=True)
        print("✓ PerforceService 초기화 성공")
        print(f"  - is_connected: {service.is_connected}")
        print(f"  - autoRevertUnchanged: {service.autoRevertUnchanged}")
        
        return adapter, service
    except Exception as e:
        print(f"✗ 코어 API 초기화 실패: {e}")
        return None, None

def test_dto_functionality():
    """DTO 기능 테스트"""
    print("=" * 50)
    print("4. DTO 기능 테스트")
    print("=" * 50)
    
    try:
        # ChangeListInfo 테스트
        cl_info = ChangeListInfo(
            id=12345,
            description="테스트 체인지리스트",
            status="pending",
            user="testuser",
            client="testclient",
            files=["file1.txt", "file2.txt"]
        )
        print("✓ ChangeListInfo 생성 성공")
        print(f"  - id: {cl_info.id}")
        print(f"  - description: {cl_info.description}")
        print(f"  - files count: {len(cl_info.files)}")
        
        cl_dict = cl_info.to_dict()
        print("✓ ChangeListInfo.to_dict() 성공")
        print(f"  - dict keys: {list(cl_dict.keys())}")
        
        # FileInfo 테스트
        file_info = FileInfo(
            path=r"C:\test\file.txt",
            inPerforce=True,
            isCheckedOut=True,
            changeList=12345,
            action="edit",
            user="testuser",
            client="testclient",
            isCurrentUser=True,
            isOthers=False,
            warnings=["경고 메시지"]
        )
        print("✓ FileInfo 생성 성공")
        print(f"  - path: {file_info.path}")
        print(f"  - isCheckedOut: {file_info.isCheckedOut}")
        print(f"  - warnings: {file_info.warnings}")
        
        file_dict = file_info.to_dict()
        print("✓ FileInfo.to_dict() 성공")
        print(f"  - dict keys: {list(file_dict.keys())}")
        
    except Exception as e:
        print(f"✗ DTO 테스트 실패: {e}")

def test_connection_workflow(use_legacy=True):
    """연결 워크플로우 테스트"""
    print("=" * 50)
    if use_legacy:
        print("5. 레거시 API 연결 워크플로우 테스트")
    else:
        print("6. 신규 코어 API 연결 워크플로우 테스트")
    print("=" * 50)
    
    workspace_name = "DongseokKim_DevStorage"  # 기존 테스트에서 사용하던 워크스페이스
    
    try:
        if use_legacy:
            p4 = Perforce()
            print("레거시 Perforce 객체 생성됨")
            
            # 연결 시도
            result = p4.connect(workspace_name)
            print(f"✓ 연결 성공: {result}")
            print(f"  - connected: {p4.connected}")
            print(f"  - workspaceRoot: {p4.workspaceRoot}")
            
            # 연결 해제
            p4.disconnect()
            print("✓ 연결 해제 성공")
            print(f"  - connected: {p4.connected}")
            
        else:
            adapter = P4Adapter()
            service = PerforceService(adapter)
            print("신규 코어 객체 생성됨")
            
            # 연결 시도
            service.connect(workspace_name)
            print("✓ 연결 성공")
            print(f"  - is_connected: {service.is_connected}")
            print(f"  - workspaceRoot: {adapter.workspaceRoot}")
            
            # 연결 해제
            service.disconnect()
            print("✓ 연결 해제 성공")
            print(f"  - is_connected: {service.is_connected}")
            
    except Exception as e:
        print(f"✗ 연결 테스트 실패: {e}")
        print(f"  오류 유형: {type(e).__name__}")
        if hasattr(e, 'args') and e.args:
            print(f"  오류 메시지: {e.args[0]}")

def test_path_normalization():
    """경로 정규화 테스트"""
    print("=" * 50)
    print("7. 경로 정규화 테스트")
    print("=" * 50)
    
    try:
        adapter = P4Adapter()
        
        test_paths = [
            "C:/test/file.txt",
            r"C:\test\file.txt",
            "test\\relative\\path.txt",
            Path("C:/test/another.txt")
        ]
        
        for path in test_paths:
            normalized = adapter._normalize_win_path(path)
            print(f"  {path} -> {normalized}")
        
        print("✓ 경로 정규화 테스트 성공")
        
    except Exception as e:
        print(f"✗ 경로 정규화 테스트 실패: {e}")

def test_error_handling():
    """에러 처리 테스트"""
    print("=" * 50)
    print("8. 에러 처리 테스트")
    print("=" * 50)
    
    try:
        adapter = P4Adapter()
        service = PerforceService(adapter)
        
        # 연결되지 않은 상태에서 작업 시도
        try:
            service.get_pending_changelists()
            print("✗ 예상된 오류가 발생하지 않음")
        except Exception as e:
            print(f"✓ 예상된 연결 오류 발생: {type(e).__name__}")
            print(f"  메시지: {str(e)}")
        
        # 잘못된 타입 전달 테스트
        try:
            service.is_in_perforce("single_path_not_list")
            print("✗ 예상된 타입 오류가 발생하지 않음")
        except Exception as e:
            print(f"✓ 예상된 타입 오류 발생: {type(e).__name__}")
            print(f"  메시지: {str(e)}")
        
    except Exception as e:
        print(f"✗ 에러 처리 테스트 실패: {e}")

def main():
    """메인 테스트 실행"""
    print("perforceCore 패키지 테스트 시작")
    print("=" * 80)
    
    test_basic_imports()
    test_legacy_initialization()
    test_core_initialization()
    test_dto_functionality()
    test_path_normalization()
    test_error_handling()
    
    # 실제 Perforce 서버 연결 테스트 (선택적)
    print("\n실제 Perforce 서버 연결 테스트를 시도합니다...")
    print("(실패할 경우 Perforce 서버 접근 권한이나 설정을 확인하세요)")
    test_connection_workflow(use_legacy=True)
    test_connection_workflow(use_legacy=False)
    
    print("\n" + "=" * 80)
    print("perforceCore 패키지 테스트 완료")

if __name__ == "__main__":
    main()
