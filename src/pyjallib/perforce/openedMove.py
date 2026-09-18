# -*- coding: utf-8 -*-
"""열린 파일의 체인지리스트 이동·수집과 그 헬퍼(사후 대조·롤백·이어받기).

`Perforce`의 Mixin이다 - `pyjallib/perforce.py`(1,671줄)를 서브패키지로 분해하면서
(2026-09-18 ExportToolsRefactor Phase 10) 메서드를 **본문 무변경으로 이동**만 했다(`P4()` 생성 호출만
패키지 이름 조회로 바꿈 - 아래 주석). 인스턴스 속성(`port`/`user`/`workspace_name`/`charset`/
`exception_level`)과 `_normalize_path(s)`는 `core.Perforce`에 있다. 특성화 Type A(`tests/perforce/`)가 계약을 고정한다.
"""

from P4 import P4, P4Exception
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Union

# 연결 객체 생성은 `pyjallib.perforce.P4`(패키지 이름)를 **호출 시점에** 조회한다.
# 소비처·테스트가 `patch("pyjallib.perforce.P4", ...)`로 대역을 꽂는 주입점을 분해 전과 같게 유지하기 위해서다
# (모듈 전역 `P4`를 쓰면 패키지 속성을 바꿔도 이 모듈에는 닿지 않는다).
from pyjallib import perforce as _perforcePackage

@dataclass
class OpenedFilesCollectResult:
    """`Perforce.collect_opened_files_into_change_list`의 결과.

    Attributes:
        succeeded: 입력 전량이 새 체인지리스트에 들어갔는가. 서밋 여부와 무관하다.
        changelist: 생성된 체인지리스트 번호. 입력이 비어 만들지 않았으면 None.
        movedCount: 대상 체인지리스트에서 확인된 파일 수.
        missingPaths: 대상 체인지리스트에서 확인되지 않은 입력 경로.
        submitted: 서밋까지 끝났는가. 요청하지 않았거나 이동이 불완전하면 False.
            요청했는데 내용 변경이 없어 빈 체인지리스트로 삭제된 경우도 False다.
        message: 사람이 읽는 결과 요약. 사용자 메시지·로그에 그대로 실린다.
    """

    succeeded: bool
    changelist: Optional[int]
    movedCount: int
    missingPaths: List[str] = field(default_factory=list)
    submitted: bool = False
    message: str = ""



class _OpenedMoveMixin:
    """열린 파일의 체인지리스트 이동·수집과 그 헬퍼(사후 대조·롤백·이어받기)."""

    def move_opened_files_to_new_change_list(self, inDescription: str, inFilePaths: List[str]) -> Dict:
        """이미 열려 있는 파일들을 새 체인지리스트로 옮긴다 (서밋하지 않음).

        입력이 **이미 열린 파일**이라는 것이 이 메서드의 계약이다. 그래서
        `p4 reopen` 하나로 끝나며, 파일 상태를 몰라서 하던 3연타
        (reopen -> edit -> add)나 `sync -k` -> `reconcile` 같은 보정이 필요 없다.

        전형적인 소비처는 UE5 임포트 흐름이다. 에디터 내부 Python API에는
        체인지리스트를 만들거나 옮기는 수단이 없어 임포터가 연 파일이 default
        체인지리스트에 남는데, 그 파일들을 에디터 밖에서 이름 붙은 CL로 모을 때
        쓴다. 다만 계약 자체에 UE5 색채는 없다 - "열린 파일 목록을 새 CL로
        모은다"는 범용 P4 연산이다.
        (Max 에셋처럼 툴 프로세스가 직접 파일을 여는 흐름에서는 최종 CL을 먼저
        만들어 체크아웃하면 되므로 이 메서드가 필요 없다.)

        서밋은 포함하지 않는다. 호출자가 검수 후 `submit_change_list`를 따로
        부르거나, pending 상태로 남겨 사람이 확인한다.

        CL 생성 -> 이동 -> 사후 대조를 **한 연결 안에서** 처리한다.
        사후 대조는 `p4 opened -c`의 `depotFile`을 `p4 where`로 로컬 경로에
        되돌려 비교한다 (`clientFile`은 클라이언트 문법이라 대조에 쓸 수 없다).

        Args:
            inDescription: 새 체인지리스트 설명 (툴 접두사 등은 호출자가 구성)
            inFilePaths: 이미 열려 있는 파일들의 로컬 경로 리스트

        Returns:
            Dict: 이동 결과
                - `succeeded` (bool): 입력 전량이 대상 CL에 들어갔으면 True
                - `changelist` (Optional[int]): 생성된 체인지리스트 번호
                - `movedCount` (int): 대상 CL에서 확인된 파일 수
                - `missingPaths` (List[str]): 대상 CL에서 확인되지 않은 입력 경로

        Raises:
            ValueError: inFilePaths가 리스트가 아닌 경우
            P4Exception: P4 작업이 실패한 경우. 이때 옮긴 파일을 default
                체인지리스트로 되돌리고 빈 CL을 삭제한 뒤 예외를 전파한다
                (파일 내용은 리버트하지 않는다 - 이동만 되돌린다).

        Note:
            일부 파일이 열려 있지 않아 이동되지 않은 경우는 예외가 아니라
            `succeeded=False` + `missingPaths`로 보고하고 CL을 유지한다.
            호출자가 원인을 진단할 수 있도록 남기는 것이며, 이 상태로 서밋하면
            누락된 파일 없이 부분 제출이 되므로 서밋 전에 반드시 확인해야 한다.
        """
        if not isinstance(inFilePaths, list):
            raise ValueError("inFilePaths must be a list")

        if not inFilePaths:
            print("이동할 파일 목록이 비어 있어 체인지리스트를 만들지 않음")
            return {'succeeded': False, 'changelist': None, 'movedCount': 0, 'missingPaths': []}

        p4 = _perforcePackage.P4()
        p4.port = self.port
        p4.user = self.user
        p4.client = self.workspace_name
        p4.charset = self.charset
        p4.exception_level = self.exception_level

        changeListNumber = None
        try:
            p4.connect()

            normalized = self._normalize_paths(inFilePaths)

            # 1. 새 체인지리스트 생성 (default CL의 파일이 딸려오지 않도록 Files 제거)
            changeSpec = p4.run("change", "-o")[0]
            changeSpec["Description"] = inDescription
            if "Files" in changeSpec:
                del changeSpec["Files"]
            changeListNumber = int(p4.save_change(changeSpec)[0].split()[1])
            print(f"체인지리스트 생성: {changeListNumber}")

            # 2. 열린 파일 이동 (reopen 단독 - 입력이 '열린 파일'임이 계약)
            p4.run("reopen", "-c", str(changeListNumber), *normalized)

            # 3. 사후 대조 - "예외 안 났다"는 "옮겨졌다"가 아니다
            movedComparable = self._collect_comparable_paths_in_change_list(
                p4, changeListNumber, normalized
            )
            missingPaths = [
                path for path in normalized
                if self._comparable_path(path) not in movedComparable
            ]

            if missingPaths:
                print(f"체인지리스트 {changeListNumber}로 이동되지 않은 파일 {len(missingPaths)}개: {missingPaths}")

            return {
                'succeeded': not missingPaths,
                'changelist': changeListNumber,
                'movedCount': len(normalized) - len(missingPaths),
                'missingPaths': missingPaths
            }
        except P4Exception as e:
            print(f"열린 파일의 체인지리스트 이동 실패: {e}")
            if changeListNumber is not None:
                self._rollback_change_list_move(p4, changeListNumber, inFilePaths)
            raise
        finally:
            if p4.connected():
                p4.disconnect()

    def collect_opened_files_into_change_list(
        self,
        inDescription: str,
        inFilePaths: List[str],
        inShouldSubmit: bool = False,
    ) -> OpenedFilesCollectResult:
        """이미 열려 있는 파일들을 새 체인지리스트로 모으고, 요청 시 서밋까지 이어 준다.

        `move_opened_files_to_new_change_list`(CL 생성 → reopen → 사후 대조)의 결과를
        해석해 서밋 여부를 결정하는 오케스트레이션이다. 세 익스포트 툴이 각자 들고
        있던 "이동 결과 해석 → 조건부 서밋" 코드를 한 벌로 합쳤다(2026-09-18
        ExportToolsRefactor Phase 1). 계약에 UE5 색채는 없다 - "열린 파일을 이름 붙은
        CL로 모으고 필요하면 서밋한다"는 범용 P4 연산이다.

        규칙:
            - 이동이 **전량 성공**(`succeeded=True`)일 때만 서밋을 시도한다. 일부가
              대상 CL에서 확인되지 않으면 CL을 pending으로 **유지**하고 서밋을 중단한다
              (부분 제출 방지 - 호출자가 `missingPaths`로 원인을 진단한다).
            - `inShouldSubmit=False`면 이동만 하고 pending으로 남긴다(사람 검수 흐름).
            - 서밋이 `False`를 돌려주면(내용 변경 없음 → 빈 CL 삭제) `submitted=False`로
              보고한다. 이것은 오류가 아니라 정상 경로다(`submit_change_list` 독스트링).

        Args:
            inDescription: 새 체인지리스트 설명(툴 접두사 등은 호출자가 구성). 빈 문자열은
                거부한다 - 이름 없는 CL은 사람이 검수할 수 없다.
            inFilePaths: 이미 열려 있는 파일들의 로컬 경로 리스트. 비어 있으면 CL을
                만들지 않고 `succeeded=False`로 보고한다.
            inShouldSubmit: 전량 이동 후 서밋까지 할지. 기본값 False(pending 유지).

        Returns:
            OpenedFilesCollectResult: 이동·서밋 결과와 사람이 읽는 요약

        Raises:
            ValueError: `inDescription`이 비어 있거나 `inFilePaths`가 리스트가 아닌 경우
            P4Exception: 이동 또는 서밋 중 P4 작업이 실패한 경우. 그대로 전파한다 -
                이동 실패는 `move_opened_files_to_new_change_list`가 롤백을 마친 뒤이고,
                서밋 실패는 CL이 pending으로 남아 있으므로 호출자가 구분해 보고한다.
        """
        if not isinstance(inDescription, str) or not inDescription.strip():
            raise ValueError("inDescription must be a non-empty string")

        moveResult = self.move_opened_files_to_new_change_list(inDescription, inFilePaths)
        changelist = moveResult.get('changelist')
        movedCount = int(moveResult.get('movedCount', 0))
        missingPaths = list(moveResult.get('missingPaths', []))

        if not moveResult.get('succeeded'):
            if changelist is None:
                message = "이동할 파일 목록이 비어 있어 체인지리스트를 만들지 않았습니다"
            else:
                message = (
                    f"체인지리스트 {changelist}에 {len(missingPaths)}개 파일이 이동되지 않아 "
                    f"서밋을 중단했습니다 (이동 {movedCount}개, 체인지리스트는 pending으로 유지)"
                )
            print(message)
            return OpenedFilesCollectResult(
                succeeded=False,
                changelist=changelist,
                movedCount=movedCount,
                missingPaths=missingPaths,
                submitted=False,
                message=message,
            )

        if not inShouldSubmit:
            message = f"체인지리스트 {changelist}에 {movedCount}개 파일 이동 (pending 유지)"
            print(message)
            return OpenedFilesCollectResult(
                succeeded=True,
                changelist=changelist,
                movedCount=movedCount,
                missingPaths=[],
                submitted=False,
                message=message,
            )

        submitted = bool(self.submit_change_list(changelist))
        if submitted:
            message = f"체인지리스트 {changelist} 제출 완료 ({movedCount}개 파일)"
        else:
            message = (
                f"체인지리스트 {changelist}는 내용 변경이 없어 빈 체인지리스트로 삭제되었습니다 "
                "(제출할 파일 없음)"
            )
        print(message)
        return OpenedFilesCollectResult(
            succeeded=True,
            changelist=changelist,
            movedCount=movedCount,
            missingPaths=[],
            submitted=submitted,
            message=message,
        )

    def _collect_comparable_paths_in_change_list(self, p4: P4, change_list_number: int,
                                                 file_paths: List[str]) -> set:
        """대상 체인지리스트에 실제로 들어간 파일들의 비교 키 집합을 만든다.

        `p4 opened -c`의 `clientFile`은 클라이언트 문법이라 로컬 경로와 대조할 수
        없으므로, `depotFile`을 `p4 where` 매핑으로 로컬 경로에 되돌린 뒤
        `_comparable_path`로 정규화한다.

        Args:
            p4: 연결된 P4 인스턴스
            change_list_number: 확인할 체인지리스트 번호
            file_paths: 정규화된 로컬 파일 경로 리스트

        Returns:
            set: 대상 CL에 열려 있는 파일들의 비교용 경로 키 집합
        """
        try:
            opened = p4.run("opened", "-c", str(change_list_number), *file_paths)
        except P4Exception as e:
            # 대상 CL에 파일이 하나도 없으면 에러가 날 수 있다 (정상 - 전량 미이동)
            print(f"체인지리스트 {change_list_number} 사후 대조 조회 결과 없음: {e}")
            return set()

        if not opened:
            return set()

        depot_to_local = self._map_depot_to_local(p4, file_paths)

        movedComparable = set()
        for file_info in opened:
            if not isinstance(file_info, dict):
                continue
            local_file = depot_to_local.get(file_info.get("depotFile", ""), "")
            if local_file:
                movedComparable.add(self._comparable_path(local_file))
        return movedComparable

    def _rollback_change_list_move(self, p4: P4, change_list_number: int,
                                   file_paths: List[str]) -> None:
        """이동 실패 시 파일을 default CL로 되돌리고 빈 체인지리스트를 삭제한다.

        **파일 내용은 리버트하지 않는다.** 갓 임포트된 에셋을 리버트하면 디스크의
        작업 결과가 사라지므로, 되돌리는 대상은 "CL 이동"뿐이다. 먼저 파일을
        default로 빼내 CL을 비운 뒤 삭제하므로 `delete_change_list` 내부의
        `revert`는 대상이 없어 무해하게 지나간다.

        정리 실패는 본래 예외를 가리지 않도록 경고만 남긴다.

        Args:
            p4: 연결된 P4 인스턴스
            change_list_number: 되돌릴 체인지리스트 번호
            file_paths: 이동을 시도했던 파일 경로 리스트
        """
        try:
            normalized = self._normalize_paths(file_paths)
            p4.run("reopen", "-c", "default", *normalized)
        except P4Exception as e:
            print(f"이동 롤백(default 복귀) 실패 (무시하고 계속): {e}")

        try:
            p4.run("change", "-d", str(change_list_number))
            print(f"이동 실패로 생성된 체인지리스트 삭제: {change_list_number}")
        except P4Exception as e:
            print(f"체인지리스트 {change_list_number} 삭제 실패 (무시하고 계속): {e}")

    @staticmethod
    def _comparable_path(path: str) -> str:
        """경로 비교용 키를 만든다 (구분자/대소문자 차이 흡수).

        Args:
            path: 비교할 경로 문자열

        Returns:
            str: 슬래시 통일 + 소문자화된 비교 키
        """
        return str(path).replace("\\", "/").lower()

    def _map_depot_to_local(self, p4: P4, file_paths: List[str]) -> Dict[str, str]:
        """`p4 where`로 depot 경로 -> 로컬 절대경로 매핑을 만든다.

        `p4 opened` 출력의 `clientFile`은 클라이언트 문법
        (`//워크스페이스명/...`)이라 로컬 절대경로와 직접 대조할 수 없다.
        열린 파일을 입력 경로와 맞추려면 `depotFile`을 키로 삼고 `p4 where`가
        돌려주는 `path`(로컬 절대경로)로 변환해야 한다.

        Args:
            p4: 연결된 P4 인스턴스
            file_paths: 정규화된 로컬 파일 경로 리스트

        Returns:
            Dict[str, str]: {depot 경로: 로컬 절대경로}. 매핑 실패 시 빈 딕셔너리.
        """
        depot_to_local: Dict[str, str] = {}
        try:
            for mapping in p4.run("where", *file_paths):
                if isinstance(mapping, dict) and "unmap" not in mapping and mapping.get("depotFile"):
                    depot_to_local[mapping["depotFile"]] = mapping.get("path", "")
        except P4Exception as e:
            print(f"p4 where 매핑 실패 (열린 파일 식별이 depot 경로 기준으로 동작): {e}")
        return depot_to_local

    def _takeover_opened_files(self, p4: P4, file_paths: List[str], change_list_number: Union[int, str]) -> Dict[str, str]:
        """대상 체인지리스트가 아닌 곳에 열려 있는 파일들을 대상 CL로 이어받는다.

        `p4 opened`(-a 미사용)는 현재 워크스페이스의 오픈만 반환하므로, 여기서
        잡히는 파일은 전부 자기 클라이언트의 pending CL(또는 default)에 열린
        파일이다. 안전하게 이어받을 수 있으므로 예외를 던지는 대신
        `p4 reopen -c`로 대상 CL로 이동시킨다. (p4 edit/add의 -c 플래그는 이미
        열린 파일을 다른 CL로 이동시키지 않으므로 reopen이 필요하다.)

        Args:
            p4: 연결된 P4 인스턴스
            file_paths: 정규화된 로컬 파일 경로 리스트
            change_list_number: 대상 체인지리스트 번호 (숫자 또는 "default")

        Returns:
            Dict[str, str]: {비교용 경로 키(_comparable_path): 오픈 액션} 딕셔너리.
                현재 열려 있는 파일만 포함된다(이어받은 파일 + 이미 대상 CL에
                있던 파일). 열려 있지 않은 파일은 포함되지 않는다.
        """
        target_cl = str(change_list_number)

        # 현재 워크스페이스에서 열린 파일 조회
        try:
            opened = p4.run("opened", *file_paths)
        except P4Exception as e:
            # 파일이 열려있지 않으면 에러가 발생할 수 있음 (정상)
            if "not opened" in str(e):
                return {}
            raise

        if not opened:
            return {}

        # opened 출력은 depot/client 문법이므로 로컬 경로 매핑을 만든다
        depot_to_local = self._map_depot_to_local(p4, file_paths)

        opened_actions: Dict[str, str] = {}
        reopen_targets = []
        source_changelists = set()
        for file_info in opened:
            if not isinstance(file_info, dict):
                continue
            depot_file = file_info.get("depotFile", "")
            local_file = depot_to_local.get(depot_file, depot_file)
            opened_actions[self._comparable_path(local_file)] = file_info.get("action", "")

            existing_cl = file_info.get("change", "")
            if existing_cl != target_cl:
                reopen_targets.append(depot_file)
                if existing_cl and existing_cl != "default":
                    source_changelists.add(existing_cl)
                print(f"파일이 체인지리스트 {existing_cl}에 열려있어 {target_cl}(으)로 이어받음(reopen): {depot_file}")

        if reopen_targets:
            p4.run("reopen", "-c", target_cl, *reopen_targets)
            self._delete_emptied_changelists(p4, source_changelists)

        return opened_actions

    def _delete_emptied_changelists(self, p4: P4, changelist_numbers: Union[set, List[str]]) -> None:
        """이어받기로 파일이 빠져나가 비게 된 pending CL들을 삭제한다.

        고아 빈 CL이 누적되는 것을 막는 정리 단계다. 조회/삭제 실패는
        본 작업에 영향을 주지 않도록 경고만 남기고 계속한다
        (셸브 파일이 있는 CL 등은 p4가 삭제를 거부한다).

        Args:
            p4: 연결된 P4 인스턴스
            changelist_numbers: 파일이 빠져나간 원본 CL 번호 목록 (default 제외)
        """
        for changelist in changelist_numbers:
            try:
                remaining = p4.run("opened", "-c", str(changelist))
                if remaining:
                    continue
                p4.run("change", "-d", str(changelist))
                print(f"이어받기로 비게 된 체인지리스트 삭제: {changelist}")
            except P4Exception as e:
                print(f"체인지리스트 {changelist} 정리 실패 (무시하고 계속): {e}")
