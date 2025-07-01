import sys
import os

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib
pyjallib.reload_modules()

from pyjallib.ue5.skeletalMeshImporter import SkeletalMeshImporter

testImporter = SkeletalMeshImporter(inContentRootPrefix=r"D:\root\Omni\Content\Omni", inFbxRootPrefix=r"E:\DevStorage_root\DevStorage")
result = testImporter.import_skeletal_mesh(inFbxFile=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\LongPolo\Lower\SK_Sh_Human_M_LongPolo_Lower.fbx", inFbxSkeletonPath=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx")
result = testImporter.import_skeletal_mesh(inFbxFile=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\LongPolo\Shoes\SK_Sh_Human_M_LongPolo_Shoes.fbx", inFbxSkeletonPath=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx")
result = testImporter.import_skeletal_mesh(inFbxFile=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\LongPolo\Upper\SK_Sh_Human_M_LongPolo_Upper.fbx", inFbxSkeletonPath=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx")
