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

---

## 주의 사항

1. **경로 정규화:** P4는 경로 대소문자나 슬래시 방향에 민감할 수 있습니다. `_normalize_path`를 통해 항상 절대 경로로 변환하여 사용합니다.
2. **빈 체인지리스트:** 파일이 없는 체인지리스트는 제출 시 삭제됩니다. (Perforce 기본 동작)
