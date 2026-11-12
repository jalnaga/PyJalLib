# 개발 절차

현재 역할·작업 배치·승인·통합 절차는 [JalHarness 작업 흐름](../../../workflow.md)을 따른다. 아래 문서는 PyJal 기술 주의점과 과거 사례를 제공하며 옛 운영 절차를 다시 활성화하지 않는다.

- [작업 결과와 학습 원료 보존](archiving_process.md) - 작업 증거를 보존하는 절차와 지식을 정제하는 절차를 분리한다.
- [Module Replacement Manual](module_replacement.md) - 이 문서는 기존 모듈을 새로운 구현으로 교체할 때 따르는 표준 절차입니다.
- [New Module Creation Manual](new_module_creation.md) - 이 문서는 새로운 Python 모듈(패키지)을 처음부터 생성할 때 따르는 표준 절차입니다.
- [P4 Deploy Step (배포 국면)](p4_deploy.md) - Git 변경분을 Perforce 배포 경로로 대응시키고 파일·CL·실행 출처를 확인한다.
- [요구 분석과 작업 분해](planning_guide.md) - 의도·범위·실측·검증 조건을 연결해 실행 가능한 계획을 작성한다.
- [Project Setup (셋업 국면)](project_setup.md) - 신규 프로젝트(툴/라이브러리) 생성 시의 명명·스캐폴딩 규약. Windows 환경(PowerShell 기본).
- [Python Packaging & Deploy (uv/hatch/PyPI + DCC venv 연동)](python_packaging.md) - uv/hatchling으로 패키지를 빌드·배포(PyPI/uvx)하고, 그 패키지를 DCC(3ds Max) 내장 Python에 연동할 때의 재사용 패턴. 출처: 2026-07-08~09 / PyJal3DSMCP PyPI/uvx 전환.
- [변경 검토 기준](review_guide.md) - 동작 계약·의존성·검증 증거·영향 범위를 검토한다.
- [구현과 검증의 작업 루프](task_loop.md) - 합의된 범위 안에서 구현·검증·기록을 진행하고 계약이 바뀌는 지점을 구분한다.
- [저장소 격리와 검증 후 반영](worktree_workflow.md) - 독립 저장소·동시 작업·배포본의 출처를 유지하면서 변경을 반영한다.
