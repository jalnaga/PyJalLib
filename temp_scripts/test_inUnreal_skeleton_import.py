import sys

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = r'J:\My Drive\Programming\Python\PyJalLib-interchange-debug\src'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

from pyjallib.ue5.inUnreal.interchangeSkeletonImporter import InterchangeSkeletonImporter

# 새 인터페이스: 직접 경로 지정
fbxPath = r'E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx'
destinationPath = r'/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3'
assetName = r'SK_Sh_Human_M_BaseSkeleton3'  # 선택적: 빈 문자열이면 FBX 파일명 기반 자동 생성

skeletonImporter = InterchangeSkeletonImporter()

# assetName이 비어있으면 None으로 처리
actualAssetName = assetName if assetName else None

result = skeletonImporter.import_skeleton(
    inFbxPath=fbxPath,
    inDestinationPath=destinationPath,
    inAssetName=actualAssetName
)
