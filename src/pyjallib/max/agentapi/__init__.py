# -*- coding: utf-8 -*-
"""PyJalLib 3ds Max 에이전트 인터페이스 — 에이전트가 본·애니·Biped·레이어·스킨·FBX·이름 기능을 JSON 인자로 호출한다.

이 패키지는 하위 모듈을 재노출하지 않는다. 함수는 하위 모듈에서 직접 가져와 호출한다.
하위 모듈 이름은 ``pyjallib.max.header``의 서비스 이름(``jal.bone`` 등)을 그대로 따른다.
각 하위 모듈 docstring에 함수 목록·부작용·사전 조건이 있다.

하위 모듈 목록:
    bone — 본 생성, 스킨 본 판정·링크·속성, 계층 순 정렬 [none, scene]
        create_nub_bone, link_skin_bone, is_skin_bone, set_skin_bone_property,
        get_skin_bone_ori_bone, set_skin_bone_parent, sort_bones_by_hierarchy,
        create_skin_bones, create_skin_bones_from_biped, is_bip_skin_bone
    anim — 월드 트랜스폼 베이크, 키 삭제, 트랜스폼 저장·복원, 평균 변환 계산, 로컬 이동 [none, scene]
        bake_world_transforms, delete_keys_in_range, match_anim_transform, save_xform,
        set_xform, get_average_position_transform, get_average_rotation_transform, move_local
    bip — Biped COM·그룹 조회, Biped 판정, BIP 파일 입출력, 피규어 모드 [none, scene, file]
        get_biped_coms, get_biped_group_nodes, is_biped_object, load_bip_file,
        save_bip_file, set_biped_figure_mode
    layer — 레이어 노드 조회·검색, 노드로 레이어 만들기, 부모 레이어 지정 [none, scene]
        get_layer_nodes, find_layers, create_layer_from_nodes, set_parent_layer
    fbx — 노드를 선택해 FBX로 내보내기(선택·익스포터 설정이 바뀐 채 남음), FBX 가져오기 [scene, file]
        export_fbx, import_fbx
    skin — Skin 모디파이어 조회, 스킨 파일 불러오기·저장(패널에 열린 Skin), 스킨 최적화(선택된 노드) [none, scene, file]
        get_skin_modifiers, load_skin, optimize_skin, save_skin
    constraint — 트랜스폼 컨트롤러를 기본형으로 접는다 [scene]
        collapse_transform_controllers
    align — 노드 회전을 마지막 노드에 맞춘다 [scene]
        align_rotation_to_last
    helper — 빈 Point 헬퍼를 만든다 [scene]
        create_empty_point
    sel — 노드의 의존 노드를 모은다(선택하지 않음) [none]
        collect_dependencies
    dependent — 익스포트 관련 노드를 모은다(원본이 결과를 선택) [scene]
        collect_export_related_nodes
    name — 이름 규칙으로 이름을 분해·조합하고 설정을 조회한다 [none]
        parse_name, combine_name, get_name_index, get_naming_config_path,
        get_name_separator, get_name_parts
    attribute — 노드의 커스텀 어트리뷰트 정의를 지운다 [scene]
        remove_attribute_def
    ue5Skeleton — Biped 스킨 본을 UE5 스켈레톤 규칙으로 회전·이름 변경·본 추가 [scene]
        rotate_biped_skin_bones_to_ue5, rename_biped_skin_bones_to_ue5,
        add_ue5_spine_skin_bones, add_ue5_neck_skin_bones, create_ue5_knuckle_skin_bones
    rig — 트위스트·볼륨 본 생성과 재생성 [scene]
        create_twist_bones, rebuild_twist_bones, create_volume_bones, rebuild_volume_bones

호출 예:
    from pyjallib.max.agentapi import bone; result = bone.sort_bones_by_hierarchy(["Bip001 Spine", "Bip001 Pelvis"])

공통 계약:
    인자는 JSON 기본형만 받고 노드는 이름·handle·NodeRef dict로 지정한다. 반환은 JSON 직렬화
    가능한 dict다. 장면·파일을 바꾸는 함수는 readback(created·modified·deleted·details·warnings)을
    돌려준다. 실패는 ``pyjallib.max.agentSupport.AgentApiError``로 던지며 ``str(exc)``는
    ``"<CODE>: <message>"``다. 어떤 함수도 대화상자나 창을 띄우지 않는다.
    원본이 바꾸는 선택·Modify 패널·FBX 익스포터 설정은 되돌리지 않는다(각 함수 docstring 참조).

사전 조건:
    3ds Max의 Python에서 pyjallib(agentSupport 포함)이 import 가능해야 한다.
    이 패키지와 하위 모듈은 import할 때 pymxs·header를 불러오지 않고 장면도 바꾸지 않는다.
    pymxs와 header는 각 함수 안에서 지연 획득한다.
"""
