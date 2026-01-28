# UE5 임포트 후 Perforce 체인지리스트 관리 워크플로우

UE5로 애니메이션을 임포트한 후, 생성된 .uasset 파일들을 자동으로 새로운 Perforce 체인지리스트로 이동하고 서밋하는 워크플로우입니다.

---

## 문제 상황

언리얼 에디터에서 애니메이션을 임포트하면:
1. .uasset 파일이 생성됨
2. 자동으로 Perforce Default 체인지리스트에 체크아웃됨
3. 여러 애니메이션을 임포트하면 Default에 파일이 누적되어 관리가 어려움

**제약 사항:**
- 언리얼 에디터 내부에는 체인지리스트를 조작하는 Python API가 없음
- 외부 Python 스크립트로 Perforce 체인지리스트를 관리해야 함

---

## 해결 방안

### 1. 워크플로우 개요

```
[UE5 임포트] → [.uasset 생성] → [Default CL에 체크아웃됨]
    ↓
[외부 Python 스크립트 실행]
    ↓
[새 CL 생성] → [파일 reopen] → [서밋]
```

### 2. 구현 위치

- **모듈:** `func_ue5Import.py`의 `UE5ImportService` 클래스
- **메서드:** `move_assets_to_new_changelist(asset_paths, description)`

### 3. 코드 패턴

```python
def move_assets_to_new_changelist(
    self,
    inAssetPaths: List[str],
    inDescription: str
) -> Tuple[bool, str]:
    """임포트된 UE5 애셋을 새 체인지리스트로 이동 및 서밋"""

    # P4Sync 인스턴스 생성 (omniP4 워크스페이스)
    p4sync = P4Sync()

    try:
        omniP4 = p4sync.omniP4

        # 1. 새 체인지리스트 생성
        change_result = omniP4.create_change_list(inDescription)
        cl_number = change_result.get("id") or change_result.get("change")

        if not cl_number:
            return (False, "체인지리스트 생성에 실패했습니다.")

        try:
            # 2. 파일을 새 체인지리스트로 reopen
            omniP4.edit_change_list(cl_number, add_file_paths=inAssetPaths)

            # 3. 개발 모드가 아니면 서밋
            if not pathAndFiles.default.isDevelopmentMode:
                submit_result = omniP4.submit_change_list(cl_number)
                if submit_result is False:
                    return (False, "체인지리스트가 비어 있어 서밋하지 않았습니다.")
                return (True, f"Submitted as changelist {cl_number}")
            else:
                return (True, f"[DEV MODE] 파일이 체인지리스트 {cl_number}로 이동되었습니다")

        except P4Exception as e:
            # Rollback: 생성된 체인지리스트 삭제
            try:
                omniP4.delete_change_list(cl_number)
            except:
                pass
            return (False, f"파일 이동 중 오류 발생: {str(e)}")

    except Exception as e:
        return (False, f"예기치 않은 오류 발생: {str(e)}")
    finally:
        # 리소스 정리
        p4sync.close()
```

### 4. UI 통합

애니메이션 저장 워크플로우에서 자동 호출:

```python
# Part 5: UE5 임포트
ue5Result, ue5Message, contentPath = self.ue5ImportService.import_animation_from_json(jsonFilePath)

if ue5Result:
    # Part 6: 임포트된 애셋을 새 체인지리스트로 이동
    self._move_imported_assets_to_changelist(contentPath)

    # Part 7: 원래 MAX 파일 다시 열기
    self.exportService.load_max_file(fileFullPath)
```

---

## 체인지리스트 설명 형식

Save 워크플로우와 동일한 형식 사용:

```python
description = self.exportService.p4Sync.prefix + " Import Anim File\n- " + animName
```

예시:
```
[이름] Import Anim File
- A_Nm_GHDtBully_M_Battle_Action_Fist_MonsterSkill_4
```

---

## 주의 사항

1. **워크스페이스 구분:**
   - DevStorage 파일: `p4Sync.devStorageP4`
   - Omni/UE5 파일: `p4Sync.omniP4` ← 임포트된 .uasset은 여기

2. **개발 모드:**
   - `pathAndFiles.default.isDevelopmentMode`가 True면 서밋하지 않음
   - 체인지리스트 생성 및 파일 이동만 수행

3. **경로 형식:**
   - 입력: UE5 Content 경로 (`D:/root/Omni/Content/Omni/.../AnimName`)
   - .uasset 파일 탐색: 폴더 내부의 `*.uasset` 패턴 사용

4. **에러 처리:**
   - reopen 실패 시 생성된 체인지리스트 삭제 (rollback)
   - 항상 `p4sync.close()`로 리소스 정리

---

## 참고 문서

- `.ai_context/references/integrations/perforce_pattern.md` - Perforce 통합 패턴
- `.ai_context/references/ue5/interchange_pipeline.md` - UE5 임포트 파이프라인
