import sys
import os

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib
pyjallib.reload_modules()

from pyjallib.ue5.inUnreal.skeletalMeshImporter import SkeletalMeshImporter

testImporter = SkeletalMeshImporter(inContentRootPrefix=r"D:\root\Omni\Content\Omni", inFbxRootPrefix=r"E:\DevStorage_root\DevStorage")
result = testImporter.import_skeletal_mesh(
    inFbxFile=r"E:\DevStorage_root\DevStorage\Characters\Main\LeeGilyeong\Male-Child\Mesh\Casual\Lower\SK_Mn_LeeGilyeong_CM_Casual_Lower.fbx", 
    inFbxSkeletonPath=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male-Child\Mesh\BaseSkeleton\SK_Sh_Human_CM_BaseSkeleton.fbx"
)
