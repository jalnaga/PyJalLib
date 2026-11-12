# Unreal Engine

- [AnimSequence 스켈레톤 변경 방법](animsequence_skeleton_change.md) - AnimSequence의 skeleton 속성은 Python API에서 read-only입니다. 스켈레톤을 변경하려면 Consolidate + Rename 방식을 사용해야 합니다.
- [UE5 에셋 경로 메서드 비교](asset_path_methods.md) - 언리얼 에셋의 경로를 가져오는 여러 메서드의 차이점입니다.
- [UE5 Headless 모드에서 에셋 삭제](headless_asset_deletion.md) - Headless 모드(-nullrhi, -unattended)에서 에셋을 완전히 삭제하는 방법입니다.
- [UE5 헤드레스 실행 가이드](headless_execution.md) - UE5 에디터를 GUI 없이 백그라운드에서 실행하여 Python 스크립트를 자동으로 실행하는 방법입니다.
- [UE5 헤드레스 Silent 실패 진단 패턴](headless_silent_failure_diagnosis.md) - UE5 에디터 헤드레스 모드(-ExecutePythonScript=... + -unattended + -nullrhi)에서 Python 스크립트가 부분적으로만 실행되고 종료되어도, subprocess returncode는 0으로 정상 처리된다. 이 silent 실패를 호출자 측
- [UE5 임포트 후 Perforce 체인지리스트 관리 워크플로우](import_perforce_workflow.md) - UE5로 애니메이션을 임포트한 후, 생성된 .uasset 파일들을 자동으로 새로운 Perforce 체인지리스트로 이동하고 서밋하는 워크플로우입니다.
- [UE5 Interchange Pipeline 설정](interchange_pipeline.md) - Interchange Framework를 사용한 FBX 임포트 시 파이프라인 설정 방법입니다.
- [UE5 임포트: Legacy vs Interchange (현황과 선택)](legacy_vs_interchange.md) - 출처: 2026-08-03 / 20260803_AnimationBUE5Import (전수 조사 + 545건 실행).
- [UE5 Path Manipulation Rules](path_rules.md) - UE5 환경에서 파일 경로를 다룰 때 반드시 따라야 하는 규칙입니다.
- [UE5 Python 속성 접근 범위 - 미export 클래스·protected 속성 읽기/쓰기·복제와 GUID](python_property_access.md) - UE Python은 "get/set_editor_property로 아무 속성이나 다룰 수 있다"처럼 보이지만, 실제로는 노출 플래그·Python 타입
- [UE5 Python 조용히 실패하는 쓰기 경로](silent_write_paths.md) - UE5 Python API의 쓰기 경로 상당수는 실패해도 예외를 던지지 않고, False조차 돌려주지 않는다.

- [레거시 FBX 애니 임포트의 로컬 트랜스폼 진단](animation_preserve_local_transform.md) - 2026-11-11 사용자 승인 반영, 당시 환경·미검증 범위 명시.
