import os
import subprocess
import socket

class Perforce:
    """
    Perforce 버전 관리 시스템과의 상호작용을 위한 클래스입니다.
    
    이 클래스는 Perforce 명령을 실행하고, 워크스페이스를 관리하며
    Perforce 서버와의 연결을 제어하는 기능을 제공합니다.
    """
    
    def __init__(self, server=None, user=None, workspace=None):
        """
        Perforce 클래스의 인스턴스를 초기화합니다.
        
        Parameters:
            server (str, optional): Perforce 서버 주소. 기본값은 환경 변수 P4PORT 또는 "PC-BUILD:1666"
            user (str, optional): Perforce 사용자 이름. 기본값은 환경 변수 P4USER 또는 "Dev"
            workspace (str, optional): Perforce 워크스페이스 이름. 기본값은 환경 변수 P4CLIENT
        """
        self.server = server if server else os.environ.get('P4PORT', "PC-BUILD:1666") # 환경 변수 우선 사용
        self.user = user if user else os.environ.get('P4USER', "Dev") # 환경 변수 우선 사용
        self.workspace = workspace if workspace else os.environ.get('P4CLIENT')
        self.workspaceRoot = None
        self.localHostName = socket.gethostname()
        
        os.environ['P4USER'] = self.user
        os.environ['P4PORT'] = self.server
        if self.workspace:
            os.environ['P4CLIENT'] = self.workspace
        else:
            # P4CLIENT가 None이면 환경 변수에서 제거 시도 (선택적)
            if 'P4CLIENT' in os.environ:
                del os.environ['P4CLIENT']
        
        # 초기화 시 연결 확인
        self._initialize_connection()
        
    def _initialize_connection(self):
        """
        Perforce 서버와의 연결을 초기화합니다.
        
        서버 연결을 확인하고 워크스페이스 루트 경로를 설정합니다.
        
        Returns:
            str: Perforce 서버 정보 문자열
        
        Raises:
            Exception: Perforce 연결 초기화 실패 시 예외 처리
        """
        result = None
        try:
            # 서버 연결 확인 (info 명령은 가볍고 빠르게 실행됨)
            result = subprocess.run(['p4', 'info'], 
                                   capture_output=True, 
                                   text=True, 
                                   encoding="utf-8")
            
            workSpaceRootPathResult = subprocess.run(
                ['p4', '-F', '%clientRoot%', '-ztag', 'info'],
                capture_output=True, 
                text=True, 
                encoding="utf-8"
            ).stdout.strip()
            self.workspaceRoot = os.path.normpath(workSpaceRootPathResult)
            
            if result.returncode != 0:
                print(f"Perforce 초기화 중 경고: {result.stderr}")
        except Exception as e:
            print(f"Perforce 초기화 실패: {e}")
        
        return result.stdout.strip()
        
    def _run_command(self, inCommands):
        """
        Perforce 명령을 실행하고 결과를 반환합니다.
        
        Parameters:
            inCommands (list): 실행할 Perforce 명령어와 인수들의 리스트
        
        Returns:
            str: 명령 실행 결과 문자열
        """
        self._initialize_connection()
        
        commands = ['p4'] + inCommands
        result = subprocess.run(commands, capture_output=True, text=True, encoding="utf-8")
                
        return result.stdout.strip()

    def get_local_hostname(self):
        """
        현재 로컬 머신의 호스트 이름을 반환합니다.
        
        Returns:
            str: 로컬 머신의 호스트 이름
        """
        # 현재 로컬 머신의 호스트 이름을 반환합니다.
        return self.localHostName

    def get_all_clients(self):
        """
        모든 Perforce 클라이언트 워크스페이스의 이름 목록을 반환합니다.
        
        Returns:
            list: 클라이언트 워크스페이스 이름 리스트
        """
        # 모든 클라이언트 워크스페이스의 이름을 반환합니다.
        result = self._run_command(['clients'])
        clients = []
        
        if result is None:
            return clients
            
        for line in result.splitlines():
            if line.startswith('Client'):
                parts = line.split()
                if len(parts) >= 2:
                    clients.append(parts[1])
        return clients

    def get_local_workspaces(self):
        """
        현재 로컬 머신에 있는 워크스페이스 목록을 반환합니다.
        
        현재 호스트 이름으로 시작하는 모든 클라이언트를 찾습니다.
        
        Returns:
            list: 로컬 머신의 워크스페이스 이름 리스트
        """
        all_clients = self.get_all_clients()
        local_clients = []

        for client in all_clients:
            if client.startswith(self.localHostName):
                local_clients.append(client)

        return local_clients
    
    def set_workspace(self, inWorkspace):
        """
        주어진 워크스페이스로 현재 작업 환경을 전환합니다.
        
        Parameters:
            inWorkspace (str): 전환할 워크스페이스 이름
            
        Returns:
            str: 워크스페이스 정보 문자열
            
        Raises:
            ValueError: 지정된 워크스페이스가 로컬 워크스페이스 목록에 없을 경우
        """
        # 주어진 워크스페이스로 전환합니다.
        localWorkSpaces = self.get_local_workspaces()
        if inWorkspace not in localWorkSpaces:
            print(f"워크스페이스 '{inWorkspace}'는 로컬 워크스페이스 목록에 없습니다.")
            return False
        
        self.workspace = inWorkspace
        os.environ['P4CLIENT'] = self.workspace
        
        return True
    
    def sync(self, inWorkSpace=None, inPaths=None):
        """
        Perforce 워크스페이스를 최신 버전으로 동기화합니다.
        
        Parameters:
            inWorkSpace (str, optional): 동기화할 워크스페이스 이름
            inPaths (str or list, optional): 동기화할 특정 경로 또는 경로 목록
            
        Returns:
            bool: 동기화 성공 여부
        """
        # 주어진 워크스페이스를 동기화합니다.
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False
        
        # 동기화 명령 실행
        sync_command = ['sync']
        
        if inPaths:
            # 문자열로 단일 경로가 주어진 경우 리스트로 변환
            if isinstance(inPaths, str):
                inPaths = [inPaths]
                
            valid_paths = []
            for path in inPaths:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    print(f"경고: 지정된 경로 '{path}'가 로컬에 존재하지 않습니다.")
            
            if not valid_paths:
                print("유효한 경로가 없어 동기화를 진행할 수 없습니다.")
                return False
                
            # 유효한 경로들을 모두 동기화 명령에 추가
            sync_command.extend(valid_paths)
    
        self._run_command(sync_command)
        return True
        
    def get_changelists(self, inWorkSpace=None):
        """
        특정 워크스페이스의 pending 상태 체인지 리스트를 가져옵니다.
        
        Parameters:
            inWorkSpace (str, optional): 체인지 리스트를 가져올 워크스페이스 이름
            
        Returns:
            list: 체인지 리스트 정보 딕셔너리의 리스트
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return []
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return []
            
        # 체인지 리스트 명령 실행
        changes_command = ['changes']
        
        # 항상 pending 상태만 가져오도록 설정
        changes_command.extend(['-s', 'pending'])
            
        if self.workspace:
            changes_command.extend(['-c', self.workspace])
            
        result = self._run_command(changes_command)
        changes = []
        
        for line in result.splitlines():
            if line.startswith('Change'):
                parts = line.split()
                if len(parts) >= 5:
                    change_id = parts[1]
                    
                    # 설명 부분 추출
                    desc_start = line.find("'")
                    desc_end = line.rfind("'")
                    description = line[desc_start+1:desc_end] if desc_start != -1 and desc_end != -1 else ""
                    
                    changes.append({
                        'id': change_id,
                        'description': description
                    })
                    
        return changes
        
    def create_new_changelist(self, inDescription="Created by pyjallib", inWorkSpace=None):
        """
        새로운 체인지 리스트를 생성합니다.
        
        Parameters:
            inDescription (str): 체인지 리스트 설명
            inWorkSpace (str, optional): 체인지 리스트를 생성할 워크스페이스 이름
            
        Returns:
            dict: 생성된 체인지 리스트 정보 {'id': str, 'description': str} 또는 실패 시 None
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return None
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return None
            
        # 체인지 리스트 생성 명령 실행
        change_command = ['change', '-o']
        result = self._run_command(change_command)
        
        # 체인지 스펙 수정
        modified_spec = []
        for line in result.splitlines():
            if line.startswith('Description:'):
                modified_spec.append(line)
                # Add the new description, handling potential multi-line descriptions correctly
                for desc_line in inDescription.splitlines():
                    modified_spec.append(f"\t{desc_line}")
                # Skip the default empty tab line if present
                # This assumes the default spec has an empty line after Description:
                # If not, this logic might need adjustment based on actual 'p4 change -o' output
                # We'll rely on the loop structure to handle subsequent lines correctly.
                continue # Move to the next line in the original spec
            # Only append lines that are not part of the old description placeholder
            # This logic assumes the default description is just a placeholder like '<enter description here>'
            # or similar, often on a single line after 'Description:'.
            # A more robust approach might be needed if the default spec is complex.
            if not (line.startswith('\t') and 'Description:' in modified_spec[-1]):
                 modified_spec.append(line)

        # 수정된 체인지 스펙으로 체인지 리스트 생성
        create_result = subprocess.run(['p4', 'change', '-i'],
                                     input='\n'.join(modified_spec),
                                     capture_output=True,
                                     text=True,
                                     encoding="utf-8")

        # 결과에서 체인지 리스트 ID 추출
        if create_result.returncode == 0 and create_result.stdout:
            output = create_result.stdout.strip()
            # 예: "Change 12345 created."
            if 'Change' in output and 'created' in output:
                parts = output.split()
                if len(parts) >= 2:
                    change_id = parts[1]
                    return {'id': change_id, 'description': inDescription} # Return dictionary

        print(f"Failed to create changelist. Error: {create_result.stderr}") # Log error if creation failed
        return None

    def checkout_files(self, inFiles, inChangelist=None, inWorkSpace=None):
        """
        지정한 파일들을 체크아웃하고 특정 체인지 리스트에 추가합니다.
        
        Parameters:
            inFiles (list): 체크아웃할 파일 경로 리스트
            inChangelist (str, optional): 파일을 추가할 체인지 리스트 ID
            inWorkSpace (str, optional): 작업할 워크스페이스 이름
            
        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False
            
        if not inFiles:
            return False
            
        # 체크아웃 명령 실행
        edit_command = ['edit']
        
        target_changelist = inChangelist
        if not target_changelist:
            new_changelist_info = self.create_new_changelist(inDescription=f"Auto-checkout for {len(inFiles)} files")
            if not new_changelist_info:
                print("Failed to create a new changelist for checkout.")
                return False
            target_changelist = new_changelist_info['id']

        edit_command.extend(['-c', target_changelist])
        edit_command.extend(inFiles)
        
        result = self._run_command(edit_command)
        
        if len(self.get_changelist_files(target_changelist)) == 0:
            self.delete_changelist(target_changelist)
        
        return True
        
    def add_files(self, inFiles, inChangelist=None, inWorkSpace=None):
        """
        지정한 파일들을 Perforce에 추가합니다.
        
        Parameters:
            inFiles (list): 추가할 파일 경로 리스트
            inChangelist (str, optional): 파일을 추가할 체인지 리스트 ID
            inWorkSpace (str, optional): 작업할 워크스페이스 이름
            
        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False
            
        if not inFiles:
            return False
            
        # 파일 추가 명령 실행
        add_command = ['add']
        
        target_changelist = inChangelist
        if not target_changelist:
            new_changelist_info = self.create_new_changelist(inDescription=f"Auto-add for {len(inFiles)} files")
            if not new_changelist_info:
                print("Failed to create a new changelist for add.")
                return False
            target_changelist = new_changelist_info['id']

        add_command.extend(['-c', target_changelist])
        add_command.extend(inFiles)
        
        result = self._run_command(add_command)
        
        if len(self.get_changelist_files(target_changelist)) == 0:
            self.delete_changelist(target_changelist)
        
        return True
        
    def delete_files(self, inFiles, inChangelist=None, inWorkSpace=None):
        """
        지정한 파일들을 Perforce에서 삭제합니다.

        Parameters:
            inFiles (list): 삭제할 파일 경로 리스트
            inChangelist (str, optional): 파일 삭제를 추가할 체인지 리스트 ID
            inWorkSpace (str, optional): 작업할 워크스페이스 이름

        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False

        if not inFiles:
            return False

        # 파일 삭제 명령 실행
        delete_command = ['delete']

        target_changelist = inChangelist
        if not target_changelist:
            # If no changelist is specified, create a new one
            new_changelist_info = self.create_new_changelist(inDescription=f"Auto-delete for {len(inFiles)} files")
            if not new_changelist_info:
                print("Failed to create a new changelist for delete.")
                return False
            target_changelist = new_changelist_info['id']

        delete_command.extend(['-c', target_changelist])
        delete_command.extend(inFiles)

        result = self._run_command(delete_command)
        
        if len(self.get_changelist_files(target_changelist)) == 0:
            self.delete_changelist(target_changelist)
            
        return True

    def revert_changelist(self, inChangelist, inWorkSpace=None):
        """
        특정 체인지 리스트의 모든 변경 사항을 되돌립니다 (revert).

        Parameters:
            inChangelist (str): 되돌릴 체인지 리스트 ID
            inWorkSpace (str, optional): 작업할 워크스페이스 이름

        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False

        if not inChangelist:
            print("Error: Changelist ID must be provided for revert operation.")
            return False

        # Revert 명령 실행
        revert_command = ['revert', '-c', inChangelist, '//...'] # Revert all files in the changelist

        result = self._run_command(revert_command)
        # p4 revert might not return an error code even if nothing was reverted.
        # We'll assume success if the command ran. More robust checking might involve parsing 'result'.
        print(f"Revert result for CL {inChangelist}:\n{result}")
        self._run_command(['change', '-d', inChangelist])
        return True

    def submit_changelist(self, inChangelist, inDescription=None, inWorkSpace=None):
        """
        특정 체인지 리스트를 서버에 제출합니다.

        Parameters:
            inChangelist (str): 제출할 체인지 리스트 ID
            inDescription (str, optional): 제출 설명 (없으면 체인지 리스트의 기존 설명 사용)
            inWorkSpace (str, optional): 작업할 워크스페이스 이름

        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False

        if not inChangelist:
            return False

        if inDescription:
            # 체인지 리스트 스펙 가져오기
            change_spec = self._run_command(['change', '-o', inChangelist])

            # 설명 수정
            modified_spec = []
            description_lines_skipped = False
            for line in change_spec.splitlines():
                if line.startswith('Description:'):
                    modified_spec.append(line)
                    # Add the new description, handling potential multi-line descriptions correctly
                    for desc_line in inDescription.splitlines():
                        modified_spec.append(f"\t{desc_line}")
                    description_lines_skipped = True # Start skipping old description lines
                    continue

                # Skip old description lines (indented lines after Description:)
                if description_lines_skipped:
                    if line.startswith('\t') or line.strip() == '':
                        continue # Skip indented lines or empty lines within the old description
                    else:
                        description_lines_skipped = False # Reached the next field

                if not description_lines_skipped:
                    modified_spec.append(line)
            
            print(modified_spec)

            # 수정된 스펙 적용
            spec_update = subprocess.run(['p4', 'change', '-i'],
                                       input='\n'.join(modified_spec),
                                       capture_output=True,
                                       text=True,
                                       encoding="utf-8")

            if spec_update.returncode != 0:
                print(f"Error updating changelist spec for {inChangelist}: {spec_update.stderr}")
                return False

        self._run_command(['submit', '-c', inChangelist])
        self.delete_empty_changelists()
        return True

    def get_changelist_files(self, inChangelist, inWorkSpace=None):
        """
        체인지 리스트에 포함된 파일 목록을 가져옵니다.
        
        Parameters:
            inChangelist (str): 체인지 리스트 ID
            inWorkSpace (str, optional): 작업할 워크스페이스 이름
            
        Returns:
            list: 파일 정보 딕셔너리의 리스트
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return []
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return []
            
        opened_result = self._run_command(['opened', '-c', inChangelist])
        files = []
        
        for line in opened_result.splitlines():
            if '#' in line:
                file_path = line.split('#')[0].strip()
                action = line.split('for ')[1].split(' ')[0] if 'for ' in line else ''
                
                files.append(file_path)
                
        return files
    
    def delete_changelist(self, inChangelist, inWorkSpace=None):
        """
        빈 체인지 리스트를 삭제합니다.
        
        Parameters:
            inChangelist (str): 삭제할 체인지 리스트 ID
            inWorkspace (str, optional): 작업할 워크스페이스 이름
            
        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False
            
        if not inChangelist:
            print("Error: Changelist ID must be provided for delete operation.")
            return False
        
        # 체인지 리스트의 파일 목록을 확인합니다
        files = self.get_changelist_files(inChangelist)
        if files:
            print(f"Error: Changelist {inChangelist} is not empty. It contains {len(files)} files.")
            return False
            
        # 빈 체인지 리스트를 삭제합니다
        delete_result = self._run_command(['change', '-d', inChangelist])
        
        if 'deleted' in delete_result:
            return True
        else:
            return False

    def delete_empty_changelists(self, inWorkSpace=None):
        """
        빈 체인지 리스트를 삭제합니다.
        
        Parameters:
            inWorkSpace (str, optional): 작업할 워크스페이스 이름
            
        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False
        
        # 모든 체인지 리스트 가져오기
        changes = self.get_changelists()
        
        for change in changes:
            if len(self.get_changelist_files(change['id'])) == 0:
                self.delete_changelist(change['id'])
        
        return True

    def upload_files(self, inFiles, inDescription=None, inWorkSpace=None):
        """
        지정한 파일들을 Perforce에 Submit 합니다.
        
        만약 파일들이 Depot에 존재하지 않으면 Add, 존재하면 Chekcout을 수행합니다.
        
        Parameters:
            inFiles (list): 업로드할 파일 경로 리스트
            inWorkSpace (str, optional): 작업할 워크스페이스 이름
        
        Returns:
            bool: 성공 여부
        """
        if inWorkSpace == None:
            if self.workspace == None:
                print(f"워크스페이스가 없습니다.")
                return False
        else:
            if not self.set_workspace(inWorkSpace):
                print(f"워크스페이스 '{inWorkSpace}'는 로컬 워크스페이스 목록에 없습니다.")
                return False
        
        if not inFiles:
            print("업로드할 파일이 지정되지 않았습니다.")
            return False
        
        # 문자열로 단일 경로가 주어진 경우 리스트로 변환
        if isinstance(inFiles, str):
            inFiles = [inFiles]
            
        # 새 체인지리스트 생성
        description = inDescription if inDescription else f"Auto-upload for {len(inFiles)} files"
        new_changelist_info = self.create_new_changelist(inDescription=description)
        if not new_changelist_info:
            print("Failed to create a new changelist for file upload.")
            return False
            
        target_changelist = new_changelist_info['id']
        
        # 파일들이 이미 디포에 있는지 확인
        files_to_add = []
        files_to_edit = []
        
        for file_path in inFiles:
            # 파일 상태 확인 (디포에 있는지 여부)
            fstat_result = self._run_command(['fstat', file_path])
            
            if 'no such file' in fstat_result.lower() or not fstat_result:
                # 디포에 없는 파일 - 추가 대상
                files_to_add.append(file_path)
            else:
                # 디포에 있는 파일 - 체크아웃 대상
                files_to_edit.append(file_path)
        
        # 파일 추가 (있는 경우)
        if files_to_add:
            add_command = ['add', '-c', target_changelist]
            add_command.extend(files_to_add)
            self._run_command(add_command)
        
        # 파일 체크아웃 (있는 경우)
        if files_to_edit:
            edit_command = ['edit', '-c', target_changelist]
            edit_command.extend(files_to_edit)
            self._run_command(edit_command)
        
        # 체인지리스트에 파일이 제대로 추가되었는지 확인
        files_in_changelist = self.get_changelist_files(target_changelist)
        
        if not files_in_changelist:
            # 파일 추가에 실패한 경우 빈 체인지리스트 삭제
            self.delete_changelist(target_changelist)
            print("파일을 체인지리스트에 추가하는 데 실패했습니다.")
            return False
            
        print(f"파일 {len(files_in_changelist)}개가 체인지리스트 {target_changelist}에 추가되었습니다.")
        return True
