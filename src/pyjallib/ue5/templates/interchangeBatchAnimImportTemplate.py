import sys

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = r'{inExtPackagePath}'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

from pyjallib.ue5.inUnreal.interchangeAnimationImporter import InterchangeAnimationImporter

# 새 인터페이스: 직접 경로 지정 (리스트 형태)
fbxPaths = {inFbxPaths}  # FBX 파일 절대 경로 리스트
destinationPaths = {inDestinationPaths}  # /Game/... 형식의 Content 목적지 경로 리스트
skeletonPaths = {inSkeletonPaths}  # /Game/... 형식의 스켈레톤 Content 경로 리스트
assetNames = {inAssetNames}  # 선택적: 에셋 이름 리스트 (빈 리스트면 None으로 처리)

animImporter = InterchangeAnimationImporter()

# assetNames가 비어있으면 None으로 처리
actualAssetNames = assetNames if assetNames else None

result = animImporter.import_animations(
    inFbxPaths=fbxPaths,
    inDestinationPaths=destinationPaths,
    inSkeletonPaths=skeletonPaths,
    inAssetNames=actualAssetNames
)
