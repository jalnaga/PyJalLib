# UE5 헤드레스 실행 가이드

UE5 에디터를 GUI 없이 백그라운드에서 실행하여 Python 스크립트를 자동으로 실행하는 방법입니다.

---

## 1. 기본 명령어 구조

### PowerShell

```powershell
& "D:\root\UE5\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" `
  "D:\root\Omni\Omni.uproject" `
  -ExecutePythonScript="경로\스크립트.py" `
  -stdout `
  -unattended `
  -nopause `
  -nosplash `
  -NOSOUND `
  -nullrhi `
  -RenderOffScreen `
  -abslog="경로\로그파일.log"
```

### CMD (Command Prompt)

```batch
"D:\root\UE5\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
  "D:\root\Omni\Omni.uproject" ^
  -ExecutePythonScript="경로\스크립트.py" ^
  -stdout ^
  -unattended ^
  -nopause ^
  -nosplash ^
  -NOSOUND ^
  -nullrhi ^
  -RenderOffScreen ^
  -abslog="경로\로그파일.log"
```

---

## 2. 플래그 설명

| 플래그 | 설명 | 필수 |
|--------|------|------|
| `-ExecutePythonScript` | 실행할 Python 스크립트의 절대 경로 | ✅ |
| `-stdout` | 콘솔 출력을 표준 출력으로 전달 | ✅ |
| `-unattended` | 무인 모드 (사용자 입력 없음) | ✅ |
| `-nopause` | 완료 시 일시정지 없음 | ✅ |
| `-nosplash` | 스플래시 화면 비활성화 | ✅ |
| `-NOSOUND` | 사운드 비활성화 | 권장 |
| `-nullrhi` | 렌더링 완전 비활성화 (가장 빠름) | 권장 |
| `-RenderOffScreen` | 오프스크린 렌더링 | 선택 |
| `-abslog` | 로그 파일의 절대 경로 지정 | 권장 |

---

## 3. Python subprocess에서 실행

### 방법 1: 리스트 형식 (권장)

```python
import subprocess

subprocess.run([
    "D:\\root\\UE5\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe",
    "D:\\root\\Omni\\Omni.uproject",
    "-ExecutePythonScript=D:\\Dropbox\\Programing\\Python\\PyJalLib-legacy-ue-import\\temp\\script.py",
    "-stdout",
    "-unattended",
    "-nopause",
    "-nosplash",
    "-NOSOUND",
    "-nullrhi",
    "-RenderOffScreen",
    "-abslog=D:\\Dropbox\\Programing\\Python\\PyJalLib-legacy-ue-import\\tests\\logs\\ue5_headless.log"
])
```

### 방법 2: 완전 백그라운드 실행 (창 숨김)

```python
import subprocess

# Windows에서 창 완전히 숨김
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE

subprocess.run([
    "D:\\root\\UE5\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe",
    "D:\\root\\Omni\\Omni.uproject",
    "-ExecutePythonScript=D:\\Dropbox\\Programing\\Python\\PyJalLib-legacy-ue-import\\temp\\script.py",
    "-stdout",
    "-unattended",
    "-nopause",
    "-nosplash",
    "-NOSOUND",
    "-nullrhi",
    "-RenderOffScreen",
    "-abslog=D:\\Dropbox\\Programing\\Python\\PyJalLib-legacy-ue-import\\tests\\logs\\ue5_headless.log"
], startupinfo=startupinfo)
```

### 방법 3: 함수화 (재사용 가능)

```python
import subprocess
from pathlib import Path

def run_ue5_headless(
    engine_path: str,
    project_path: str,
    script_path: str,
    log_path: str,
    hide_window: bool = True
) -> subprocess.CompletedProcess:
    """
    UE5를 헤드레스 모드로 실행하여 Python 스크립트 실행

    Args:
        engine_path: UnrealEditor-Cmd.exe 경로
        project_path: .uproject 파일 경로
        script_path: 실행할 Python 스크립트 경로
        log_path: UE5 로그 파일 저장 경로
        hide_window: 창 숨김 여부 (기본: True)

    Returns:
        subprocess.CompletedProcess: 실행 결과
    """
    cmd = [
        engine_path,
        project_path,
        f"-ExecutePythonScript={script_path}",
        "-stdout",
        "-unattended",
        "-nopause",
        "-nosplash",
        "-NOSOUND",
        "-nullrhi",
        "-RenderOffScreen",
        f"-abslog={log_path}"
    ]

    if hide_window:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return subprocess.run(cmd, startupinfo=startupinfo, capture_output=True, text=True)
    else:
        return subprocess.run(cmd, capture_output=True, text=True)


# 사용 예시
result = run_ue5_headless(
    engine_path="D:\\root\\UE5\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe",
    project_path="D:\\root\\Omni\\Omni.uproject",
    script_path="D:\\Dropbox\\Programing\\Python\\PyJalLib-legacy-ue-import\\temp\\script.py",
    log_path="D:\\Dropbox\\Programing\\Python\\PyJalLib-legacy-ue-import\\tests\\logs\\ue5_headless.log"
)

print(f"Return code: {result.returncode}")
print(f"Output: {result.stdout}")
```

---

## 4. 로그 파일 위치 지정

### 기본 동작

- `-log` 플래그만 사용: UE5 프로젝트의 `Saved/Logs/` 폴더에 저장
- 로그 파일명: `{ProjectName}.log`

### 사용자 지정 경로

`-abslog` 플래그로 절대 경로 지정:

```bash
-abslog="D:\Dropbox\Programing\Python\PyJalLib-legacy-ue-import\tests\logs\ue5_headless.log"
```

**장점**:
- 프로젝트 폴더 외부에 로그 저장 가능
- 자동화 스크립트에서 로그 수집 용이
- 여러 프로젝트의 로그를 한 곳에 모을 수 있음

---

## 5. 출력 확인

헤드레스 실행 시 결과는 다음 위치에서 확인할 수 있습니다:

1. **Python 스크립트의 로그**: 스크립트 내부에서 설정한 로그 파일
   - 예: `tests/logs/test_ue5_task16.log`

2. **UE5 엔진 로그**: `-abslog`로 지정한 파일
   - 예: `tests/logs/ue5_headless.log`
   - UE5의 모든 로그 메시지 포함 (LogPython, LogFileHelpers 등)

3. **stdout/stderr**: `subprocess.run(capture_output=True)`로 캡처
   - `result.stdout`: 표준 출력
   - `result.stderr`: 에러 출력
   - `result.returncode`: 종료 코드 (0이면 성공)

---

## 6. 주의사항

### 창 숨김 관련

- PowerShell의 `&` 연산자는 **터미널에서 직접 실행할 때만** 필요
- Python subprocess에서는 `&` 없이 실행
- `startupinfo`를 사용하면 에디터 창이 **완전히 보이지 않음**

### 경로 관련

- 모든 경로는 **절대 경로** 사용 권장
- Windows 경로는 `\\` (이스케이프) 또는 `/` (정규화) 사용
- PowerShell에서는 백틱(`` ` ``)으로 줄바꿈, CMD에서는 `^` 사용

### 성능 최적화

- `-nullrhi`: 렌더링 비활성화 (가장 큰 성능 향상)
- `-NOSOUND`: 사운드 비활성화
- `-RenderOffScreen`: 오프스크린 렌더링 (필요시)

---

## 7. 참고 자료

- Epic Games 공식 가이드: https://dev.epicgames.com/community/snippets/J5R1/unreal-engine-run-headless-unreal-editor-with-python-script
- UE5 Command Line Arguments: https://docs.unrealengine.com/5.3/en-US/command-line-arguments-in-unreal-engine/
