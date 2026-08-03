import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r'{inExtPackagePath}'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from legacyBaseImporter import LegacyBaseImporter
from legacyStaticMeshImporter import LegacyStaticMeshImporter
from importResultWriter import write_import_result

# 입력 변수
fbxPath = r'{inFbxPath}'
destinationPath = r'{inDestinationPath}'
assetName = r'{inAssetName}'

# 결과 JSON 경로 (선택) - 비어 있으면 기록을 생략한다 (구 툴 하위호환)
resultJsonPath = r'{inResultJsonPath}'

# prefix 자동 추론
contentRootPrefix, fbxRootPrefix = LegacyBaseImporter.infer_prefixes_from_paths(destinationPath, fbxPath)

# 임포터 초기화 및 실행
staticMeshImporter = LegacyStaticMeshImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

# assetName이 빈 문자열이면 None으로 처리 (자동 생성)
assetNameArg = assetName if assetName else None

# 임포터는 서밋하지 않는다. 연 파일은 default 체인지리스트에 남고,
# 이름 붙은 CL로의 이동과 서밋은 결과 JSON을 회수한 툴 프로세스가 담당한다.
importResults = []
try:
    result = staticMeshImporter.import_static_mesh(fbxPath, inAssetName=assetNameArg)
    importResults.append(result)
except Exception as e:
    # 실패해도 그 시점까지의 결과를 남긴 뒤 예외를 그대로 전파한다
    write_import_result(resultJsonPath, importResults, inSuccess=False, inError=str(e))
    raise

write_import_result(resultJsonPath, importResults, inSuccess=True)
