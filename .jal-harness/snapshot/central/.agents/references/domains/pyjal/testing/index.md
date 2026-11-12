# 테스트

- [Type A: 완전 자동화 테스트 (Console Only)](automated_console.md) - 순수 Python 테스트의 import·mock·수집 범위를 격리한다.
- [Type C: 실행 기반 로그 분석 테스트 (Console Trigger + Log File)](console_trigger_log.md) - 1. 터미널에서 실행하고, 로그 파일로 검증한다.
- [Debug Process (디버깅 프로토콜)](debug_process.md) - 실패를 재현하고 원인과 계약을 분리해 수정·회귀 확인한다.
- [판별력 실증 (이 테스트가 무엇을 잡는가를 증명한다)](discriminating_power.md) - 결함을 실제로 주입하고 어느 테스트가 왜 실패하는지 확인하는 방법.
- [Test Process Overview](test_process.md) - 우리는 코드의 품질과 안정성을 보장하기 위해 4가지 테스트 전략을 사용한다. 테스트 대상의 성격에 따라 적절한 전략을 선택하고, 해당 가이드 문서를 로드하여 수행하라.
- [testKit 패턴 - DCC 독립 테스트 자동화 인프라](testkit_pattern.md) - testKit 전체가 Python stdlib만 사용. loguru, pymxs, unreal, PySide 금지.
- [Type D: 코드 기반 UI 자동화 테스트 (QtTest Simulation)](ui_automation.md) - QtTest로 UI 상태와 이벤트를 검증하고 헤드리스의 한계를 구분한다.
- [Type B: 유저 주도 테스트 (User Action + Log) - 최후 수단](user_driven_log.md) - 출처: 2026-06-17 / PyJalFacialBuilder / 메쉬 포즈 Pick 다이얼로그
- [automated_console](automated_console/index.md) - 하위 주제 색인.
- [discriminating_power](discriminating_power/index.md) - 하위 주제 색인.
- [ui_automation](ui_automation/index.md) - 하위 주제 색인.
