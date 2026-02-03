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
fbxPaths = {inFbxPaths}
destinationPath = r'{inDestinationPath}'
skeletonPath = r'{inSkeletonPath}'

# prefix 자동 추론 (첫 번째 FBX 경로 사용)
if len(fbxPaths) > 0:
    contentRootPrefix, fbxRootPrefix = LegacyBaseImporter.infer_prefixes_from_paths(destinationPath, fbxPaths[0])
else:
    raise ValueError("fbxPaths 리스트가 비어있습니다")

# 임포터 초기화 및 실행
animImporter = LegacyAnimationImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

# 모든 애니메이션이 같은 스켈레톤을 사용하므로, 스켈레톤 경로를 리스트로 변환
skeletonPaths = [skeletonPath] * len(fbxPaths)

result = animImporter.import_animations(fbxPaths, inSkeletonContentPaths=skeletonPaths)
