# Active Task List

## Feature: 애니메이션 재임포트 시 스켈레톤 변경 불가 버그 수정

**해결 방안**: ~~하이브리드 접근법 (B + C 결합)~~ → **방안 D: Consolidate + Rename**

### 완료된 태스크 (방안 B+C - 실패)

- [x] ~~**Task 1**: `legacyAnimationImporter.py`에 기존 에셋 스켈레톤 사전 변경 로직 추가~~ (실패)
- [x] ~~**Task 2**: 스켈레톤이 다른 경우 사전 변경 로직 구현~~ (실패 - read-only)
- [x] ~~**Task 3**: FbxImportUI 최적화 옵션 적용~~ (단독 효과 없음)

### 구현 태스크 (방안 D - 신규)

- [x] **Task 7**: `create_import_task()`에서 스켈레톤 변경 감지 로직 수정
  - `import_animation()`에 스켈레톤 변경 감지 및 Consolidate+Rename 플로우 분기 추가
  - `_get_target_skeleton()`, `_needs_skeleton_swap()` 헬퍼 메서드 추가
  - 스켈레톤 동일 시 기존 방식 유지

- [x] **Task 8**: Consolidate + Rename 헬퍼 메서드 구현
  - `_swap_skeleton_via_consolidate()` 메서드 추가
  - 임시 이름으로 새 에셋 임포트
  - `consolidate_assets()` 호출로 참조 리다이렉트
  - Redirector 삭제 후 `rename_asset()` 호출로 이름 복원

- [x] **Task 9**: 기존 실패 코드 제거/정리
  - Task 1-2의 `set_editor_property('skeleton')` 코드 제거
  - 기존 에셋 로드 및 스켈레톤 사전 변경 로직 제거

### 테스트 태스크

- [x] **Task 4**: 재임포트 시 스켈레톤 변경 동작 검증 ✅ (2026-02-04)
  - 기존 스켈레톤 X로 임포트된 애니메이션을 스켈레톤 Y로 재임포트
  - 재임포트 후 스켈레톤이 Y로 변경되었는지 확인
  - 결과: SKEL_Sh_Human_M_BaseSkeleton → SKEL_Sh_Human_F_BaseSkeleton 변경 성공

- [x] **Task 5**: 참조 무결성 검증 ✅ (2026-02-04)
  - 기존 에셋 참조가 유지되는지 확인
  - 외부 에셋(AnimBP 등)의 참조가 깨지지 않는지 검증
  - 결과: 에셋 경로 유지, Redirector 정리, 참조자 유지 모두 통과

### P1 태스크 (권장) - 스킵

- [ ] **Task 6**: 로깅 및 결과 검증 로직 추가
  - 스켈레톤 변경 성공/실패 시 로그 메시지 출력
  - 재임포트 후 실제 스켈레톤 vs 의도한 스켈레톤 비교 검증

---

**총 태스크 수:** 6개 (신규 3개 + 테스트 2개 + P1 1개)
**최종 완료:** 5/6 완료 (P1 제외 모든 태스크 완료)
**완료 일자:** 2026-02-04
