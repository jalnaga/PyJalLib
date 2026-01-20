import sys

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = r'{inExtPackagePath}'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

from pyjallib.ue5.inUnreal.interchangeAnimationImporter import InterchangeAnimationImporter

# 새 인터페이스: 직접 경로 지정
fbxPath = r'{inFbxPath}'
destinationPath = r'{inDestinationPath}'
skeletonPath = r'{inSkeletonPath}'  # /Game/... 형식의 스켈레톤 Content 경로
assetName = r'{inAssetName}'  # 선택적: 빈 문자열이면 FBX 파일명 기반 자동 생성

animImporter = InterchangeAnimationImporter()

# assetName이 비어있으면 None으로 처리
actualAssetName = assetName if assetName else None

result = animImporter.import_animation(
    inFbxPath=fbxPath,
    inDestinationPath=destinationPath,
    inSkeletonPath=skeletonPath,
    inAssetName=actualAssetName
)
