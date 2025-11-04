# 간단한 P4 체인지리스트 생성 테스트

## 목적

P4 직접 사용과 pyjallib 사용의 결과를 명확하게 비교하기 위한 최소한의 테스트 파일입니다.

## 파일 설명

### 1. `simple_test_p4_direct.py`
- **P4 Python을 직접 사용**하여 체인지리스트 생성
- **워크스페이스 수동 입력** 필요 (파일 상단의 `WORKSPACE_NAME` 변수 수정)
- orvlib 의존성 없음

### 2. `simple_test_pyjallib.py`
- **pyjallib 라이브러리 사용**하여 체인지리스트 생성
- **orvlib에서 워크스페이스 자동 감지**
- pyjallib와 orvlib 필요

## 실행 방법

### 방법 1: 3ds Max에서 실행

```python
# P4 직접 사용 테스트
# 1. simple_test_p4_direct.py 파일을 열어서 WORKSPACE_NAME을 수정
# 2. 3ds Max에서 실행:
exec(open(r"D:\Dropbox\Programing\Python\PyJalLib\tests\simple_test_p4_direct.py").read())

# pyjallib 사용 테스트
exec(open(r"D:\Dropbox\Programing\Python\PyJalLib\tests\simple_test_pyjallib.py").read())
```

### 방법 2: 명령줄에서 실행

```bash
# P4 직접 사용 테스트 (먼저 파일에서 WORKSPACE_NAME 수정)
python tests\simple_test_p4_direct.py

# pyjallib 사용 테스트
python tests\simple_test_pyjallib.py
```

## 준비사항

### P4 직접 테스트 (`simple_test_p4_direct.py`)
1. 파일을 열어서 `WORKSPACE_NAME` 변수 수정
   ```python
   WORKSPACE_NAME = "YourWorkspaceName"  # ← 실제 워크스페이스 이름으로 변경
   ```

### pyjallib 테스트 (`simple_test_pyjallib.py`)
1. orvlib가 설치되어 있어야 함
2. 워크스페이스 자동 감지되므로 수정 불필요

## 예상 결과

### 정상 환경
두 테스트 모두:
- ✓✓✓ 성공! ✓✓✓
- 생성된 체인지 번호 표시
- 동일한 결과

### 문제 환경
두 테스트 모두:
- ✗✗✗ 실패 ✗✗✗
- 같은 에러 메시지 (예: `Required parameter 'data' not set!`)
- 동일한 실패

## 출력 예시

### 성공 시:
```
================================================================================
✓✓✓ 성공! ✓✓✓
================================================================================
결과: ['Change 33682 created.']
생성된 체인지 번호: 33682
```

### 실패 시:
```
================================================================================
✗✗✗ 실패 (P4Exception) ✗✗✗
================================================================================
에러 타입: P4Exception
에러 메시지: Operation 'dm-UpdateChangeSpec' failed.
Required parameter 'data' not set!

전체 스택 트레이스:
--------------------------------------------------------------------------------
Traceback (most recent call last):
  ...
```

## 비교 분석

두 테스트를 **연속으로 실행**하여:
1. 둘 다 성공하면: 환경에 문제 없음
2. 둘 다 실패하면: 환경 문제이며, 에러 메시지 동일해야 함
3. 결과가 다르면: 코드 문제 (이론적으로 불가능)

## 문제 해결

### "워크스페이스를 찾을 수 없습니다" (pyjallib 테스트)
- orvlib가 제대로 설치되었는지 확인
- devStorageP4 또는 omniP4가 초기화되었는지 확인

### "P4 연결 실패"
- P4 서버가 실행 중인지 확인
- 워크스페이스 이름이 올바른지 확인
- 네트워크 연결 확인

### "pyjallib 모듈 import 실패"
- PyJalLib 경로가 올바른지 확인
- sys.path에 src 디렉토리가 추가되었는지 확인

