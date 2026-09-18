# -*- coding: utf-8 -*-
"""체인지리스트 CRUD·제출·리버트·조회.

`Perforce`의 Mixin이다 - `pyjallib/perforce.py`(1,671줄)를 서브패키지로 분해하면서
(2026-09-18 ExportToolsRefactor Phase 10) 메서드를 **본문 무변경으로 이동**만 했다(`P4()` 생성 호출만
패키지 이름 조회로 바꿈 - 아래 주석). 인스턴스 속성(`port`/`user`/`workspace_name`/`charset`/
`exception_level`)과 `_normalize_path(s)`는 `core.Perforce`에 있다. 특성화 Type A(`tests/perforce/`)가 계약을 고정한다.
"""

from P4 import P4Exception
from typing import List, Optional, Dict

# 연결 객체 생성은 `pyjallib.perforce.P4`(패키지 이름)를 **호출 시점에** 조회한다.
# 소비처·테스트가 `patch("pyjallib.perforce.P4", ...)`로 대역을 꽂는 주입점을 분해 전과 같게 유지하기 위해서다
# (모듈 전역 `P4`를 쓰면 패키지 속성을 바꿔도 이 모듈에는 닿지 않는다).
from pyjallib import perforce as _perforcePackage


class _ChangeListMixin:
    """체인지리스트 CRUD·제출·리버트·조회."""

    def create_change_list(self, description: str) -> Dict:
        """
        새 체인지리스트 생성

        Args:
            description: 체인지리스트 설명

        Returns:
            Dict: 생성된 체인지리스트 정보 {'id', 'description', 'status', 'user', 'client'}
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # 새 체인지 스펙 가져오기
            change_spec = p4.run("change", "-o")[0]
            change_spec["Description"] = description

            # Default CL 파일이 새 CL로 이동하지 않도록 Files 필드 제거
            if "Files" in change_spec:
                del change_spec["Files"]

            # 저장
            result = p4.save_change(change_spec)[0]

            # 생성된 번호 파싱 ("Change 12345 created")
            cl_number = int(result.split()[1])

            # 상세정보 조회
            cl_info = p4.fetch_change(cl_number)

            return {
                'id': cl_number,
                'description': cl_info.get('Description', '').strip(),
                'status': cl_info.get('Status', ''),
                'user': cl_info.get('User', ''),
                'client': cl_info.get('Client', '')
            }
        except P4Exception as e:
            print(f"체인지리스트 생성 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def delete_change_list(self, change_list_number: int) -> bool:
        """
        체인지리스트 삭제 (파일이 있으면 리버트 후 삭제)

        Args:
            change_list_number: 삭제할 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # 1. 체인지리스트의 파일 리버트
            try:
                p4.run("revert", "-c", str(change_list_number), "//...")
                print(f"체인지리스트 {change_list_number}의 파일 리버트 완료")
            except P4Exception:
                # 리버트할 파일이 없을 수 있음
                pass

            # 2. 체인지리스트 삭제
            p4.run("change", "-d", str(change_list_number))
            print(f"체인지리스트 {change_list_number} 삭제 완료")
            return True
        except P4Exception as e:
            print(f"체인지리스트 삭제 실패 (CL {change_list_number}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def delete_empty_change_list(self) -> List[int]:
        """
        현재 클라이언트의 모든 빈 펜딩 체인지리스트 삭제

        Returns:
            List[int]: 삭제된 체인지리스트 번호 리스트
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name
            deleted_cls = []

            # 대기 중인 체인지리스트 조회
            changes = p4.run("changes", "-s", "pending", "-u", user, "-c", client)

            for change in changes:
                cl_number = int(change.get('change', 0))
                if cl_number == 0:
                    continue

                # 체인지리스트에 파일이 있는지 확인
                try:
                    opened = p4.run("opened", "-c", str(cl_number))
                    # 파일이 있으면 건너뛰기
                    if opened:
                        continue
                except P4Exception:
                    # 파일이 없으면 에러 발생 (정상 - 빈 CL)
                    pass

                # 빈 체인지리스트 삭제 시도
                try:
                    p4.run("change", "-d", str(cl_number))
                    deleted_cls.append(cl_number)
                    print(f"빈 체인지리스트 삭제: {cl_number}")
                except P4Exception as e:
                    # 삭제 실패는 경고만 출력하고 계속 진행
                    print(f"체인지리스트 삭제 실패 (CL {cl_number}): {e}")

            return deleted_cls
        except P4Exception as e:
            print(f"빈 체인지리스트 삭제 작업 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def submit_change_list(self, change_list_number: int, auto_revert_unchanged: bool = True) -> bool:
        """
        체인지리스트 제출

        `auto_revert_unchanged=True`(기본)이면 제출 전에 `p4 revert -a`를 실행한다.
        이는 **내용이 depot과 같아진 파일을 체인지리스트에서 내린다**는 뜻이다.
        다른 경로(예: 에디터 내부 자동 서밋)가 이미 같은 내용을 제출한 뒤라면
        워크스페이스 = depot이 되어 CL의 파일이 전부 내려가고, 남은 빈 CL은
        `p4 change -d`로 삭제된 뒤 `False`가 반환된다. 즉 **"서밋했다고 믿었는데
        depot 이력에 CL이 없다"는 증상의 정상 동작 경로**다.
        내용 무변경 파일까지 이력에 남겨야 하면 `False`를 전달한다.

        Args:
            change_list_number: 제출할 체인지리스트 번호
            auto_revert_unchanged: 변경되지 않은 파일 자동 리버트 여부. 기본값 True.

        Returns:
            bool: 제출 성공 여부 (False인 경우 빈 체인지리스트로 삭제됨)
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # 1. 변경 없는 파일 리버트
            if auto_revert_unchanged:
                try:
                    p4.run("revert", "-a", "-c", str(change_list_number))
                except P4Exception:
                    # 리버트 실패는 무시 (파일이 없을 수 있음)
                    pass

            # 2. 제출할 파일 확인
            opened = p4.run("opened", "-c", str(change_list_number))
            if not opened:
                # 빈 체인지리스트 삭제
                p4.run("change", "-d", str(change_list_number))
                return False

            # 3. 제출
            p4.run("submit", "-c", str(change_list_number))
            return True
        except P4Exception as e:
            print(f"체인지리스트 제출 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def revert_change_list(self, change_list_number: int) -> bool:
        """
        체인지리스트의 모든 파일 리버트 및 체인지리스트 삭제

        Args:
            change_list_number: 리버트할 체인지리스트 번호

        Returns:
            bool: 성공 여부
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # 1. 파일 리버트
            try:
                p4.run("revert", "-c", str(change_list_number), "//...")
            except P4Exception:
                # 리버트할 파일이 없을 수 있음
                pass

            # 2. 빈 체인지리스트 삭제
            p4.run("change", "-d", str(change_list_number))
            return True
        except P4Exception as e:
            print(f"체인지리스트 리버트 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def edit_change_list(self, change_list_number: int, description: Optional[str] = None,
                        add_file_paths: Optional[List[str]] = None,
                        remove_file_paths: Optional[List[str]] = None) -> Dict:
        """
        체인지리스트 수정

        Args:
            change_list_number: 수정할 체인지리스트 번호
            description: 새 설명 (None이면 변경하지 않음)
            add_file_paths: 추가할 파일 경로 리스트
            remove_file_paths: 제거할 파일 경로 리스트

        Returns:
            Dict: 수정된 체인지리스트 정보
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            # Description 변경
            if description is not None:
                change_spec = p4.fetch_change(change_list_number)
                change_spec["Description"] = description
                p4.save_change(change_spec)

            # 파일 추가 (reopen)
            if add_file_paths:
                normalized = self._normalize_paths(add_file_paths)
                p4.run("reopen", "-c", str(change_list_number), *normalized)

            # 파일 제거 (default CL로 reopen)
            if remove_file_paths:
                normalized = self._normalize_paths(remove_file_paths)
                p4.run("reopen", "-c", "default", *normalized)

            # 수정된 정보 반환
            cl_info = p4.fetch_change(change_list_number)
            return {
                'id': change_list_number,
                'description': cl_info.get('Description', '').strip(),
                'status': cl_info.get('Status', ''),
                'user': cl_info.get('User', ''),
                'client': cl_info.get('Client', '')
            }
        except P4Exception as e:
            print(f"체인지리스트 수정 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_pending_change_list(self) -> List[Dict]:
        """
        대기 중인 체인지리스트 목록 조회

        Returns:
            List[Dict]: 체인지리스트 정보 리스트
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name

            # 대기 중인 체인지리스트 조회 (설명 포함)
            changes = p4.run("changes", "-l", "-s", "pending", "-u", user, "-c", client)

            result = []
            for change in changes:
                result.append({
                    'id': int(change.get('change', 0)),
                    'description': change.get('desc', '').strip(),
                    'status': change.get('status', ''),
                    'user': change.get('user', ''),
                    'client': change.get('client', '')
                })

            return result
        except P4Exception as e:
            print(f"체인지리스트 조회 실패: {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_change_list_by_number(self, change_list_number: int) -> Dict:
        """
        번호로 체인지리스트 조회

        Args:
            change_list_number: 조회할 체인지리스트 번호

        Returns:
            Dict: 체인지리스트 정보
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            cl_info = p4.fetch_change(change_list_number)

            return {
                'id': change_list_number,
                'description': cl_info.get('Description', '').strip(),
                'status': cl_info.get('Status', ''),
                'user': cl_info.get('User', ''),
                'client': cl_info.get('Client', '')
            }
        except P4Exception as e:
            print(f"체인지리스트 조회 실패 (번호: {change_list_number}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_change_list_by_description(self, description: str) -> Dict:
        """
        설명으로 체인지리스트 조회 (정확히 일치하는 첫 번째 항목)

        Args:
            description: 찾을 설명

        Returns:
            Dict: 체인지리스트 정보 (없으면 빈 딕셔너리)
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name

            changes = p4.run("changes", "-l", "-s", "pending", "-u", user, "-c", client)

            for change in changes:
                desc = change.get('desc', '').strip()
                if desc == description:
                    return {
                        'id': int(change.get('change', 0)),
                        'description': desc,
                        'status': change.get('status', ''),
                        'user': change.get('user', ''),
                        'client': change.get('client', '')
                    }

            return {}
        except P4Exception as e:
            print(f"체인지리스트 조회 실패 (설명: {description}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_change_list_by_description_pattern(self, description_pattern: str,
                                               exact_match: bool = False) -> List[Dict]:
        """
        설명 패턴으로 체인지리스트 검색

        Args:
            description_pattern: 검색할 패턴
            exact_match: True면 정확히 일치, False면 부분 일치

        Returns:
            List[Dict]: 매칭되는 체인지리스트 리스트
        """
        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level
        try:
            p4.connect()

            user = p4.user
            client = self.workspace_name

            changes = p4.run("changes", "-l", "-s", "pending", "-u", user, "-c", client)

            result = []
            for change in changes:
                desc = change.get('desc', '').strip()

                if exact_match:
                    if desc == description_pattern:
                        result.append({
                            'id': int(change.get('change', 0)),
                            'description': desc,
                            'status': change.get('status', ''),
                            'user': change.get('user', ''),
                            'client': change.get('client', '')
                        })
                else:
                    if description_pattern in desc:
                        result.append({
                            'id': int(change.get('change', 0)),
                            'description': desc,
                            'status': change.get('status', ''),
                            'user': change.get('user', ''),
                            'client': change.get('client', '')
                        })

            return result
        except P4Exception as e:
            print(f"체인지리스트 검색 실패 (패턴: {description_pattern}): {e}")
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def get_default_change_list(self) -> Dict:
        """
        기본 체인지리스트 정보 반환

        Returns:
            Dict: 기본 체인지리스트 정보 (id는 'default')
        """
        return {
            'id': 'default',
            'description': 'Default Change',
            'status': 'pending',
            'user': '',
            'client': self.workspace_name or ''
        }
