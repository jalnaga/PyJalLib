import sys

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = r'J:\My Drive\Programming\Python\PyJalLib-interchange-anim-debug\src'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

from pyjallib.ue5.inUnreal.interchangeAnimationImporter import InterchangeAnimationImporter

# 새 인터페이스: 직접 경로 지정
fbxPath = r'E:\DevStorage_root\DevStorage\Characters\NPC\Human\Male\Animation\Neutral\Storytelling\Default\A_Nc_Human_M_Neutral_Storytelling_Default_HeadShakeThink_Loop-RBr-Enter.fbx'
destinationPath = r'/Game/Omni/Characters/NPC/Human/Male/Animation/Neutral/Storytelling/Default'
skeletonPath = r'/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3'  # /Game/... 형식의 스켈레톤 Content 경로
assetName = r'A_Nc_Human_M_Neutral_Storytelling_Default_HeadShakeThink_Loop-RBr-Enter'  # 선택적: 빈 문자열이면 FBX 파일명 기반 자동 생성

animImporter = InterchangeAnimationImporter()

# assetName이 비어있으면 None으로 처리
actualAssetName = assetName if assetName else None

result = animImporter.import_animation(
    inFbxPath=fbxPath,
    inDestinationPath=destinationPath,
    inSkeletonPath=skeletonPath,
    inAssetName=actualAssetName
)
