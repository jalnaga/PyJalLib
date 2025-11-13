"""
Perforce 모듈 단순화 버전 테스트
간단한 수동 테스트 스크립트
"""

from pyjallib.perforce import Perforce


def test_connection():
    """연결 테스트"""
    print("\n=== 연결 테스트 ===")
    p4 = Perforce()

    # 워크스페이스 이름을 환경에 맞게 수정하세요
    workspace_name = "YOUR_WORKSPACE_NAME"

    try:
        result = p4.connect(workspace_name)
        print(f"연결 성공: {result}")
        print(f"워크스페이스: {p4.workspace_name}")
        print(f"워크스페이스 루트: {p4.workspaceRoot}")

        p4.disconnect()
        print("연결 해제 완료")
    except Exception as e:
        print(f"연결 실패: {e}")


def test_create_and_delete_changelist():
    """체인지리스트 생성 및 삭제 테스트"""
    print("\n=== 체인지리스트 생성/삭제 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"

    try:
        p4.connect(workspace_name)

        # 체인지리스트 생성
        cl = p4.create_change_list("테스트 체인지리스트 - 자동 삭제 예정")
        print(f"생성된 CL: {cl}")
        print(f"  ID: {cl['id']}")
        print(f"  Description: {cl['description']}")
        print(f"  Status: {cl['status']}")

        # 체인지리스트 삭제
        result = p4.delete_empty_change_list(cl['id'])
        print(f"삭제 성공: {result}")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def test_get_pending_changelists():
    """대기 중인 체인지리스트 조회 테스트"""
    print("\n=== 대기 중인 체인지리스트 조회 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"

    try:
        p4.connect(workspace_name)

        # 대기 중인 체인지리스트 조회
        changelists = p4.get_pending_change_list()
        print(f"대기 중인 체인지리스트 수: {len(changelists)}")

        for cl in changelists[:5]:  # 처음 5개만 출력
            print(f"  CL {cl['id']}: {cl['description'][:50]}...")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def test_file_operations():
    """파일 작업 테스트 (체크아웃, 리버트)"""
    print("\n=== 파일 작업 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"
    test_file = "//depot/path/to/test/file.txt"  # 실제 파일 경로로 수정하세요

    try:
        p4.connect(workspace_name)

        # 체인지리스트 생성
        cl = p4.create_change_list("파일 작업 테스트")
        print(f"체인지리스트 생성: {cl['id']}")

        # 파일 체크아웃
        print(f"파일 체크아웃: {test_file}")
        p4.checkout_file(test_file, cl['id'])
        print("체크아웃 성공")

        # 파일 상태 확인
        is_checked_out = p4.is_file_checked_out(test_file)
        print(f"체크아웃 상태: {is_checked_out}")

        # 체인지리스트 리버트
        print(f"체인지리스트 리버트: {cl['id']}")
        p4.revert_change_list(cl['id'])
        print("리버트 및 삭제 완료")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def test_batch_file_operations():
    """배치 파일 작업 테스트"""
    print("\n=== 배치 파일 작업 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"
    test_files = [
        "//depot/path/to/test/file1.txt",
        "//depot/path/to/test/file2.txt",
    ]  # 실제 파일 경로로 수정하세요

    try:
        p4.connect(workspace_name)

        # 체인지리스트 생성
        cl = p4.create_change_list("배치 파일 작업 테스트")
        print(f"체인지리스트 생성: {cl['id']}")

        # 여러 파일 체크아웃
        print(f"파일 체크아웃: {len(test_files)}개")
        p4.checkout_files(test_files, cl['id'])
        print("체크아웃 성공")

        # 파일 상태 확인
        status = p4.check_files_checked_out(test_files)
        print("파일 상태:")
        for path, checked_out in status.items():
            print(f"  {path}: {checked_out}")

        # 체인지리스트 리버트
        print(f"체인지리스트 리버트: {cl['id']}")
        p4.revert_change_list(cl['id'])
        print("리버트 및 삭제 완료")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def test_submit_workflow():
    """제출 워크플로우 테스트 (실제 제출하지 않음)"""
    print("\n=== 제출 워크플로우 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"

    try:
        p4.connect(workspace_name)

        # 체인지리스트 생성
        cl = p4.create_change_list("제출 테스트 - 실제 제출 안함")
        print(f"체인지리스트 생성: {cl['id']}")

        # 빈 체인지리스트 제출 시도 (자동 삭제됨)
        print("빈 체인지리스트 제출 시도...")
        result = p4.submit_change_list(cl['id'], auto_revert_unchanged=True)
        print(f"제출 결과: {result} (False는 빈 CL이 자동 삭제됨을 의미)")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def test_changelist_search():
    """체인지리스트 검색 테스트"""
    print("\n=== 체인지리스트 검색 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"

    try:
        p4.connect(workspace_name)

        # 테스트용 체인지리스트 생성
        test_desc = "검색 테스트 체인지리스트 - 고유한 설명"
        cl = p4.create_change_list(test_desc)
        print(f"테스트 CL 생성: {cl['id']}")

        # 번호로 조회
        found_by_number = p4.get_change_list_by_number(cl['id'])
        print(f"번호로 조회: {found_by_number['id']}")

        # 설명으로 조회
        found_by_desc = p4.get_change_list_by_description(test_desc)
        print(f"설명으로 조회: {found_by_desc['id'] if found_by_desc else '찾지 못함'}")

        # 패턴으로 검색
        found_by_pattern = p4.get_change_list_by_description_pattern("검색 테스트", exact_match=False)
        print(f"패턴으로 검색: {len(found_by_pattern)}개 발견")

        # 정리
        p4.delete_empty_change_list(cl['id'])
        print("테스트 CL 삭제 완료")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def test_file_status_checks():
    """파일 상태 확인 테스트"""
    print("\n=== 파일 상태 확인 테스트 ===")
    p4 = Perforce()

    workspace_name = "YOUR_WORKSPACE_NAME"
    test_file = "//depot/path/to/test/file.txt"  # 실제 파일 경로로 수정하세요

    try:
        p4.connect(workspace_name)

        # 파일이 Perforce에 있는지 확인
        in_perforce = p4.is_file_in_perforce(test_file)
        print(f"Perforce에 존재: {in_perforce}")

        # 체크아웃 상태 확인
        is_checked_out = p4.is_file_checked_out(test_file)
        print(f"체크아웃 상태: {is_checked_out}")

        # 다른 사용자가 체크아웃했는지 확인
        by_others = p4.is_file_checked_out_by_others(test_file)
        print(f"다른 사용자 체크아웃: {by_others}")

        # 상세 정보 조회
        info = p4.get_file_checkout_info_all_users(test_file)
        print(f"상세 정보: {info}")

        p4.disconnect()
    except Exception as e:
        print(f"테스트 실패: {e}")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Perforce 단순화 버전 테스트 시작")
    print("=" * 60)

    print("\n주의: 테스트를 실행하기 전에 워크스페이스 이름과")
    print("      파일 경로를 실제 환경에 맞게 수정하세요!")
    print()

    # 기본 테스트만 실행 (파일 작업은 실제 파일 경로 필요)
    test_connection()
    test_create_and_delete_changelist()
    test_get_pending_changelists()
    test_submit_workflow()
    test_changelist_search()

    # 파일 작업 테스트는 주석 처리 (실제 파일 경로 필요)
    # test_file_operations()
    # test_batch_file_operations()
    # test_file_status_checks()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    # 개별 테스트 실행 예시:
    # test_connection()
    # test_create_and_delete_changelist()

    # 모든 테스트 실행:
    run_all_tests()
