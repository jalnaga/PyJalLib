import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r'{inExtPackagePath}'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from legacyBaseImporter import LegacyBaseImporter
from legacyAnimationImporter import LegacyAnimationImporter

# Interchange 방식의 입력 변수
fbxPath = r'{inFbxPath}'
destinationPath = r'{inDestinationPath}'
skeletonPath = r'{inSkeletonPath}'
assetName = r'{inAssetName}'

# prefix 자동 추론
contentRootPrefix, fbxRootPrefix = LegacyBaseImporter.infer_prefixes_from_paths(destinationPath, fbxPath)

# 임포터 초기화 및 실행
animImporter = LegacyAnimationImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

# assetName이 빈 문자열이면 None으로 처리 (자동 생성)
assetNameArg = assetName if assetName else None

result = animImporter.import_animation(fbxPath, inSkeletonContentPath=skeletonPath, inAssetName=assetNameArg)
