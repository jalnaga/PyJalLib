import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r'J:\My Drive\Programming\Python\PyJalLib-import-asset-save-fix\src'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from interchangeAnimationImporter import InterchangeAnimationImporter

# 새 인터페이스: 직접 경로 지정 (리스트 형태)
fbxPaths = ['E:\\DevStorage_root\\DevStorage\\Characters\\NPC\\Human\\Male\\Animation\\Neutral\\Storytelling\\Default\\A_Nc_Human_M_Neutral_Storytelling_Default_RhStop_RBr-Enter.fbx', 'E:\\DevStorage_root\\DevStorage\\Characters\\Shared\\Human\\Male\\Animation\\Neutral\\System\\Equipment\\A_Sh_Human_M_Neutral_System_Equipment_WriteBasic_Loop.fbx', 'E:\\DevStorage_root\\DevStorage\\Characters\\NormalMonster\\GumhoDistrictBully\\Male\\Animation\\Battle\\Action\\Fist\\A_Nm_GHDtBully_M_Battle_Action_Fist_MonsterSkill_1.fbx']  # FBX 파일 절대 경로 리스트
destinationPaths = ['/Game/Omni/Characters/NPC/Human/Male/Animation/Neutral/Storytelling/Default', '/Game/Omni/Characters/Shared/Human/Male/Animation/Neutral/System/Equipment', '/Game/Omni/Characters/NormalMonster/GumhoDistrictBully/Male/Animation/Battle/Action/Fist']  # /Game/... 형식의 Content 목적지 경로 리스트
skeletonPaths = ['/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3', '/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3', '/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3']  # /Game/... 형식의 스켈레톤 Content 경로 리스트
assetNames = ['A_Nc_Human_M_Neutral_Storytelling_Default_RhStop_RBr-Enter', 'A_Sh_Human_M_Neutral_System_Equipment_WriteBasic_Loop', 'A_Nm_GHDtBully_M_Battle_Action_Fist_MonsterSkill_1']  # 선택적: 에셋 이름 리스트 (빈 리스트면 None으로 처리)

animImporter = InterchangeAnimationImporter()

# assetNames가 비어있으면 None으로 처리
actualAssetNames = assetNames if assetNames else None

# 비동기 배치 임포트 실행 (병렬 처리로 속도 향상)
animImporter.import_animations_async(
    inFbxPaths=fbxPaths,
    inDestinationPaths=destinationPaths,
    inSkeletonPaths=skeletonPaths,
    inAssetNames=actualAssetNames
)
