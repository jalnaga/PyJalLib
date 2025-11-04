# P4 체인지리스트 생성 문제 진단 도구

## 목적

이 도구는 Perforce 체인지리스트 생성 시 발생하는 문제를 진단하기 위해 개발되었습니다.
특정 아티스트의 환경에서만 발생하는 문제를 파악하여 해결하는 데 사용됩니다.

## 실행 방법

### 방법 1: 3ds Max Python 콘솔에서 실행

1. 3ds Max를 실행합니다
2. MAXScript 리스너 창을 엽니다 (F11 키)
3. 다음 스크립트 중 하나를 복사하여 붙여넣습니다:

```python
import sys
sys.path.append(r"D:\Dev_Storage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages")
sys.path.append(r"D:\Dev_Storage_root\DevStorage\ExtPythonPackage\src")

from tests.p4_diagnostic_tool import run_diagnostic
run_diagnostic()  # 워크스페이스는 자동으로 감지됩니다
```

4. 스크립트를 실행합니다 (Enter 키)
5. 몇 초 후 완료 메시지가 표시됩니다

### 방법 2: 명령줄에서 실행

```bash
python tests\p4_diagnostic_tool.py
```

## 예상 소요 시간

약 10-30초

## 생성되는 파일

진단이 완료되면 다음 위치에 로그 파일이 생성됩니다:

**폴더**: `C:\Users\사용자명\Documents\PyJalLib_Diagnostics\`

**파일**:
- `p4_diagnostic_YYYYMMDD_HHMMSS.json` - 모든 진단 결과 (기계 판독용)
- `p4_diagnostic_YYYYMMDD_HHMMSS.txt` - 읽기 쉬운 텍스트 리포트

예시:
- `p4_diagnostic_20250103_143052.json`
- `p4_diagnostic_20250103_143052.txt`

## 다음 단계

진단이 완료되면 생성된 로그 파일을 개발자에게 전달해주세요.

**전달 방법**:
- 공유 폴더에 업로드
- 이메일로 전송
- 슬랙/팀스 등의 채널로 전송

**파일 크기**: 일반적으로 수십 KB ~ 수백 KB 정도입니다.

## 주의사항

1. **워크스페이스 이름**: 반드시 정확한 워크스페이스 이름을 입력해야 합니다
   - 현재 워크스페이스 이름 확인: P4V 또는 명령줄에서 `p4 info` 실행
   
2. **P4 연결 상태**: P4 서버에 연결 가능한 상태여야 합니다
   - 네트워크 연결 확인
   - P4V가 정상적으로 작동하는지 확인
   
3. **권한**: 워크스페이스에 체인지리스트를 생성할 수 있는 권한이 있어야 합니다
   - 테스트용 체인지리스트가 생성되지만 자동으로 삭제되지 않을 수 있습니다
   - 필요시 P4V에서 수동으로 삭제해주세요

## FAQ

### Q: 실행 중 에러가 발생했어요

A: 에러 메시지를 복사하여 개발자에게 전달해주세요. 가능하면 다음 정보도 함께:
- 어떤 방법으로 실행했는지 (3ds Max / 명령줄)
- 워크스페이스 이름
- 에러 메시지 전체

### Q: 로그 파일을 찾을 수 없어요

A: Documents 폴더의 PyJalLib_Diagnostics 하위 폴더를 확인해주세요.
- 경로: `C:\Users\당신의사용자명\Documents\PyJalLib_Diagnostics\`
- 폴더가 없으면 자동으로 생성됩니다

### Q: 로그 파일에 민감한 정보가 포함되나요?

A: 로그에는 다음 정보가 포함될 수 있습니다:
- 워크스페이스 이름
- 사용자명
- P4 서버 주소
- 파일 경로
- Python 버전 등 시스템 정보

패스워드나 개인 정보는 포함되지 않습니다.

### Q: 진단 도구가 체인지리스트를 생성하나요?

A: 네, 테스트 목적으로 체인지리스트가 생성될 수 있습니다.
대부분의 경우 자동으로 삭제되지만, 실패한 경우 P4V에서 수동으로 삭제해주세요.
작성자: 개발자, 설명: "PyJalLib Diagnostic Test"

## 문의

문제가 발생하거나 궁금한 점이 있으면 개발자에게 문의해주세요.

