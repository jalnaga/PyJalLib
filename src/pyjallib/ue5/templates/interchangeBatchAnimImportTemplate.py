import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r'{inExtPackagePath}'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from interchangeAnimationImporter import InterchangeAnimationImporter

# 새 인터페이스: 직접 경로 지정 (리스트 형태)
fbxPaths = {inFbxPaths}  # FBX 파일 절대 경로 리스트
destinationPaths = {inDestinationPaths}  # /Game/... 형식의 Content 목적지 경로 리스트
skeletonPaths = {inSkeletonPaths}  # /Game/... 형식의 스켈레톤 Content 경로 리스트
assetNames = {inAssetNames}  # 선택적: 에셋 이름 리스트 (빈 리스트면 None으로 처리)

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
