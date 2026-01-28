import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r"J:\My Drive\Programming\Python\PyJalLib-import-asset-save-fix\src"
inUnrealPath = extPackagePath + r"/pyjallib/ue5/inUnreal"

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from interchangeSkeletonImporter import InterchangeSkeletonImporter

# 새 인터페이스: 직접 경로 지정
fbxPath = r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton3\SK_Sh_Human_M_BaseSkeleton3.fbx"
destinationPath = r"/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3"
assetName = r"SK_Sh_Human_M_BaseSkeleton3"  # 선택적: 빈 문자열이면 FBX 파일명 기반 자동 생성

skeletonImporter = InterchangeSkeletonImporter()

# assetName이 비어있으면 None으로 처리
actualAssetName = assetName if assetName else None

result = skeletonImporter.import_skeleton(
    inFbxPath=fbxPath, inDestinationPath=destinationPath, inAssetName=actualAssetName
)
