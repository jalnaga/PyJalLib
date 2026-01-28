# Perforce Integration Pattern

`pyjallib`에서 Perforce와 상호작용할 때 사용하는 표준 패턴입니다.

---

## 핵심 원칙

1. **독립 연결 (Stateless):** 각 메서드 호출 시마다 `connect`하고 작업 후 `disconnect`합니다. 커넥션을 오래 유지하지 않습니다.
2. **예외 처리:** 모든 P4 작업은 `try-finally` 블록으로 감싸서 연결이 반드시 해제되도록 보장합니다.
3. **배치 처리:** 가능한 한 여러 파일을 한 번에 처리(`checkout_files` 등)하여 오버헤드를 줄입니다.

---

## 기본 사용 패턴 (Low Level)

직접 `P4` 클래스를 사용할 경우 다음 패턴을 따릅니다.

```python
from P4 import P4, P4Exception

p4 = P4()
p4.port = "server:1666"
p4.user = "username"
p4.client = "workspace_name"

try:
    p4.connect()
    # 작업 수행
    result = p4.run("info")
except P4Exception as e:
    # 에러 처리
    print(f"Error: {e}")
    raise
finally:
    # 반드시 연결 해제
    if p4.connected():
        p4.disconnect()
```

---

## High Level API 사용 (권장)

`pyjallib.perforce.Perforce` 클래스를 사용하면 연결 관리가 자동화됩니다.

### 1. 초기화

```python
from pyjallib.perforce import Perforce

p4_service = Perforce(port="localhost:1666", user="admin")
p4_service.connect("my_workspace")
```

### 2. 체인지리스트 생성 및 파일 작업

```python
# 1. 체인지리스트 생성
cl_info = p4_service.create_change_list("My Description")
cl_id = cl_info['id']

# 2. 파일 체크아웃 (배치)
files = ["D:/Project/file1.txt", "D:/Project/file2.txt"]
p4_service.checkout_files(files, cl_id)

# 3. 파일 추가
new_files = ["D:/Project/new_file.txt"]
p4_service.add_files(new_files, cl_id)
```

### 3. 상태 확인

```python
# 다른 사용자가 체크아웃 했는지 확인
others = p4_service.get_files_checked_out_by_others(files)
if others:
    print("Files locked by others!")
```

### 4. 체인지리스트 파일 이동 (Reopen) 및 서밋

```python
# 1. 새 체인지리스트 생성
cl_info = p4_service.create_change_list("Import animation: MyAnim")
cl_number = cl_info.get("id") or cl_info.get("change")

try:
    # 2. 기존 체크아웃된 파일들을 새 체인지리스트로 이동
    asset_paths = ["E:/OmniP4_root/Omni/Content/Anim/MyAnim.uasset"]
    p4_service.edit_change_list(cl_number, add_file_paths=asset_paths)

    # 3. 체인지리스트 서밋
    submit_result = p4_service.submit_change_list(cl_number)
    if submit_result is False:
        print("Empty changelist - automatically deleted")
    else:
        print(f"Submitted as changelist {cl_number}")

except P4Exception as e:
    # 에러 발생 시 생성된 체인지리스트 삭제 (rollback)
    try:
        p4_service.delete_change_list(cl_number)
    except:
        pass  # 삭제 실패는 무시
    raise
```

---

## 주의 사항

1. **경로 정규화:** P4는 경로 대소문자나 슬래시 방향에 민감할 수 있습니다. `_normalize_path`를 통해 항상 절대 경로로 변환하여 사용합니다.
2. **빈 체인지리스트:** 파일이 없는 체인지리스트는 제출 시 삭제됩니다. (Perforce 기본 동작)
3. **Reopen 실패 처리:** 파일을 새 체인지리스트로 이동(reopen) 중 실패하면 생성된 체인지리스트를 삭제(rollback)하여 깔끔하게 정리합니다.
4. **반환값 형식:** `create_change_list`는 워크스페이스에 따라 `{"id": 번호}` 또는 `{"change": 번호}` 형식으로 반환할 수 있으므로 두 키를 모두 확인합니다.
