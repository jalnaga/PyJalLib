import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r'{inExtPackagePath}'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from legacyBaseImporter import LegacyBaseImporter
from legacyAnimationImporter import LegacyAnimationImporter
from importResultWriter import write_import_result

# Interchange 방식의 입력 변수
fbxPaths = {inFbxPaths}
destinationPath = r'{inDestinationPath}'
skeletonPath = r'{inSkeletonPath}'

# 결과 JSON 경로 (선택) - 비어 있으면 기록을 생략한다 (구 툴 하위호환)
resultJsonPath = r'{inResultJsonPath}'

# prefix 자동 추론 (첫 번째 FBX 경로 사용)
if len(fbxPaths) > 0:
    contentRootPrefix, fbxRootPrefix = LegacyBaseImporter.infer_prefixes_from_paths(destinationPath, fbxPaths[0])
else:
    raise ValueError("fbxPaths 리스트가 비어있습니다")

# 임포터 초기화 및 실행
animImporter = LegacyAnimationImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

# 모든 애니메이션이 같은 스켈레톤을 사용하므로, 스켈레톤 경로를 리스트로 변환
skeletonPaths = [skeletonPath] * len(fbxPaths)

# import_animation() 반복 호출 방식 사용 (스켈레톤 변경 감지 기능 활용)
# 임포터는 서밋하지 않는다. 연 파일은 default 체인지리스트에 남고,
# 이름 붙은 CL로의 이동과 서밋은 결과 JSON을 회수한 툴 프로세스가 담당한다.
# 파일별 실패 격리는 하지 않는다(현행 유지) - 실패하면 그 지점까지의 결과를
# JSON에 남기고 예외를 전파해 툴이 stdout 에러 마커로 실패를 판정하게 한다.
importResults = []
try:
    for i, fbxPath in enumerate(fbxPaths):
        result = animImporter.import_animation(fbxPath, inSkeletonContentPath=skeletonPaths[i])
        importResults.append(result)
except Exception as e:
    write_import_result(resultJsonPath, importResults, inSuccess=False, inError=str(e))
    raise

write_import_result(resultJsonPath, importResults, inSuccess=True)
