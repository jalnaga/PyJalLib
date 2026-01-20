import sys

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = r'J:\My Drive\Programming\Python\PyJalLib-ue5-interchange-framework\src'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

from pyjallib.ue5.inUnreal.interchangeSkeletalMeshImporter import InterchangeSkeletalMeshImporter

fbxPath = r'E:\DevStorage_root\DevStorage\Characters\Shared\Human\Female\Mesh\Default3\Body\SK_Sh_Human_F_Default3_Body.fbx'
skeletonFbxPath = r'E:\DevStorage_root\DevStorage\Characters\Shared\Human\Female\Mesh\BaseSkeleton3\Sh_Human_F_BaseSkeleton3.fbx'

contentRootPrefix = r'/Game/'
fbxRootPrefix = r'E:\DevStorage_root\DevStorage'

skeletalMeshImporter = InterchangeSkeletalMeshImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

result = skeletalMeshImporter.import_skeletal_mesh(fbxPath, skeletonFbxPath)
