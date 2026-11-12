# 3ds Max

- [Auto Key 억제 + 블렌드 캐시 패턴](animation_auto_key_blend.md) - Auto Key가 켜진 상태에서 본 컨트롤러에 값을 쓸 때, 의도치 않은 키프레임 생성을 방지하는 패턴입니다. posController.value = ... 할당은 animButtonState와 무관하게 메쉬 변형을 정상 표시하며, animButtonState는 키프레임 생성 
- [pymxs Animation Context Managers](animation_context.md) - pymxs에서 애니메이션 키프레임을 생성할 때 사용하는 컨텍스트 매니저 패턴입니다.
- [3ds Max 네이티브 Animation Layer 래핑 (Float_Layer 의미론)](animation_layer_float_layer.md) - 출처: 2026-07-16 / PyJalFacialBuilder(+PyJalFacial) AnimSlider 레이어링. 프로브 6종 실측으로 확정.
- [쿼터니언 블렌딩 + 델타 트랜스폼 + rt.execute 제거](animation_quaternion_transform.md) - 쿼터니언 회전을 가중치로 블렌딩할 때, 성분별 덧셈은 수학적으로 잘못된 결과를 생성한다. 쿼터니언은 곱셈으로 합성해야 한다.
- [XAF 포맷 한계 + addNewKey 최적화 + 탄젠트 직렬화](animation_xaf_keys.md) - rt.LoadSaveAnimation의 로드는 노드 이름으로 매칭한다.
- [Batch Morph Target 추출 및 FBX 익스포트 패턴](batch_morph_target_extraction.md) - Morpher 모디파이어를 가진 메쉬의 모든 모프 채널을 개별 FBX 파일로 배치 익스포트하는 패턴. 여러 .max 파일을 순회하며 각 파일 내 특정 노드의 모프 채널을 추출한다.
- [Biped 피규어 모드 - 관절 위치를 프로그램으로 옮길 때](biped_figure_mode.md) - Biped는 일반 본과 달리 위치를 직접 받지 않는 노드가 있고, 받는 노드도 그 결과를 부모 회전으로
- [blend_poses() 성능 프로파일링 결과 (2026-04-09)](blend_poses_profiling.md) - 278본 x 2컨트롤러(pos + rot) = 556회의 controller.value = 설정이 매 프레임 발생한다. 각 설정은 Python → C++ COM 경계를 넘기는 IPC 호출이며, 개당 ~19μs (10.6ms / 556). 이 호출을 Python 레벨에서 줄이는 
- [어트리뷰트 홀더 모디파이어에 커스텀 어트리뷰트 붙이기](custom_attribute_modifier.md) - 출처: 2026-08-04 / 20260804_ORVRootMotion (외부 MaxScript 툴 RootMotionTools_v0.93.ms 이식).
- [Dependent 모듈 - 의존성 탐색과 수집 확장 규칙](dependent_module.md) - pyjallib.max.dependent.Dependent 클래스는 3ds Max 오브젝트의 의존성을 Handle 기반 BFS로 탐색한다. 탐색 전략은 하나다.
- [Editable Poly 서브오브젝트 - 숨김·고립·dead 구조와 헤드리스 서브오브젝트 진입](editable_poly_subobject.md) - 메쉬 검증 규칙을 "숨김 엣지 / 면 없는 엣지 / 고립 버텍스 / dead 구조" 식으로 기획하면, 그중 상당수가
- [페이셜 포즈 델타 기준 공간 - v1 parent space / v2 FacialRoot space](facial_delta_space.md) - 출처: 2026-08-28 ~ 08-29 / PyJalFacial + PyJalFacialBuilder (델타 공간 이중 지원 사이클).
- [레이어 규약 중앙화와 구 규약 씬 마이그레이션](layer_convention_migration.md) - 출처: 2026-07-28 / orvlib(레이어 규약 중앙화 · 구 규약 씬 자동 재구성 익스포트), 2026-07-29 / 20260728_LayerRemapper, 2026-07-29 / orvlib(구 BaseSkeleton 이식 제거 + 계층 정합), 2026-07-2
- [3ds Max 테스트 스크립트 패턴 (Type C 헤드레스)](max_test_pattern.md) - 3ds Max 배치 테스트의 러너·출처·프로브·결과 로그 규약.
- [3ds Max Layer Manipulation Pattern](pymxs_layer.md) - 3ds Max에서 레이어를 관리할 때 따르는 표준 패턴입니다. pyjallib 라이브러리 사용을 최우선으로 합니다.
- [pymxs 주의사항 (Pitfalls)](pymxs_pitfalls.md) - pymxs 개발 시 자주 발생하는 함정과 해결 방법입니다.
- [pymxs 주의사항 - 고급 (Pitfalls Advanced)](pymxs_pitfalls_advanced.md) - pymxs의 API별 반환값·좌표계·객체 수명과 조용한 실패 사례.
- [PySide2 슬라이더 스타일 커스터마이즈 (3ds Max)](pyside2_slider_style.md) - 따라서 "그루브 아래"에 눈금을 그리면 위젯 밖이라 보이지 않는다.
- [PySide2 UI 패턴 - blockSignals + 역인덱스 + QFrame + Container.title()](pyside2_ui_block_index_frame.md) - 외부에서 프로그래밍 방식으로 QSlider/QSpinBox 값을 변경할 때, 시그널 연쇄를 차단하여 불필요한 콜백 호출을 방지하는 패턴입니다.
- [PySide2 UI 패턴 - Container + SlotButton](pyside2_ui_container_slot.md) - 접을 수 있는 롤아웃(Container) 안에 탭 위젯을 배치하는 패턴입니다.
- [PySide2 UI 패턴 - FuzzySearchComboBox](pyside2_ui_fuzzy_combo.md) - 3ds Max 환경에서 QComboBox를 상속하면 showPopup/hidePopup 연쇄 호출이 3ds Max 메시지 루프와 충돌하여 팝업이 즉시 닫히거나 키 입력이 전달되지 않는 문제가 발생한다. QWidget 기반 커스텀 위젯 + Qt.Popup 플래그로 완전히 새로 구
- [PySide2 UI 패턴 - QLabel 말줄임 + PairLinkWidget](pyside2_ui_label_pair.md) - 라벨의 너비를 고정하고, 텍스트가 길 경우 말줄임(...) 처리하여 레이아웃 통일성을 유지하는 패턴입니다.
- [PySide2 UI 패턴 (3ds Max) - 인덱스](pyside2_ui_patterns.md) - 3ds Max 툴 개발 시 자주 사용되는 PySide2 UI 패턴 모음입니다.
- [PySide2 UI 패턴 - 시그널 전파 + 레이아웃 + 테마](pyside2_ui_signals_layout_theme.md) - 자식 위젯의 시그널을 부모 위젯으로 전파하여 상위 레벨에서 처리하는 패턴입니다.
- [PySide2 UI 패턴 - ToolState + QScrollArea + DnD](pyside2_ui_state_scroll_dnd.md) - 툴의 UI 상태(윈도우 위치/크기, Container expand/collapse)를 JSON으로 저장하고 다음 실행 시 복원하는 패턴이다.
- [PySide2 Window Parent 설정 (3DS Max)](pyside2_window.md) - 3DS Max에서 PySide2(Qt)로 UI 툴을 만들 때, 반드시 3DS Max 메인 윈도우를 parent로 설정해야 툴 윈도우가 3DS Max 창 위에 정상적으로 표시됩니다.
- [QGraphicsView 보드 패턴 (아이템 배치 · 히트 테스트 · 헤드레스 검증)](qgraphics_board.md) - u = (cos θ, -sin θ)에 투영하면 0도·90도·대각선이 한 식으로 처리된다
- [레이캐스트 가림 판정 - RayMeshGridIntersect 거동과 "가려진 면"의 정의](ray_occlusion.md) - "이 면이 다른 오브젝트에 가려졌는가"는 레이 몇 개로 끝나 보이지만, 세 군데서 조용히 틀린다. ① 레이 API가 빗나간
- [skinOps 본 ID 체계와 가중치 이전](skin_bone_id.md) - skinOps의 ID 체계는 두 종류가 있고, 구조 변경 API가 양쪽에서 ID를 민다.
- [pymxs_pitfalls_advanced](pymxs_pitfalls_advanced/index.md) - 하위 주제 색인.

- [3dsmax-mcp 안전 모드의 시작 시점과 값 해석](mcp_bridge_safe_mode.md) - 2026-11-11 사용자 승인 반영, 당시 환경·미검증 범위 명시.

- [Max에 미리 로드된 라이브러리 출처 확인](preloaded_library_origin.md) - 2026-11-11 사용자 승인 반영, 당시 환경·미검증 범위 명시.
