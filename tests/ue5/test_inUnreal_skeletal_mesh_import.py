import sys

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
# 이렇게 하면 loguru 등 외부 의존성 없이 inUnreal 모듈만 사용 가능
extPackagePath = r'J:\My Drive\Programming\Python\PyJalLib-interchange-skeletal-debug\src'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from interchangeSkeletalMeshImporter import InterchangeSkeletalMeshImporter

# 새 인터페이스: 직접 경로 지정
fbxPath = r'E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BlousonPolo\Upper\SK_Sh_Human_M_BlousonPolo_Upper.fbx'
destinationPath = r'/Game/Omni/Characters/Shared/Human/Male/Mesh/BlousonPolo/Upper'
skeletonPath = r'/Game/Omni/Characters/Shared/Human/Male/Mesh/BaseSkeleton3/SKEL_Sh_Human_M_BaseSkeleton3'  # /Game/... 형식의 스켈레톤 Content 경로
assetName = r'SK_Sh_Human_M_BlousonPolo_Upper'  # 선택적: 빈 문자열이면 FBX 파일명 기반 자동 생성

skeletalMeshImporter = InterchangeSkeletalMeshImporter()

# assetName이 비어있으면 None으로 처리
actualAssetName = assetName if assetName else None

result = skeletalMeshImporter.import_skeletal_mesh(
    inFbxPath=fbxPath,
    inDestinationPath=destinationPath,
    inSkeletonPath=skeletonPath,
    inAssetName=actualAssetName
)
