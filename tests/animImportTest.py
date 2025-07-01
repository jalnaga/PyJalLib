import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib
pyjallib.reload_modules()
from orvlib import pathAndFiles

from pyjallib.ue5.animationImporter import AnimationImporter
from pyjallib.ue5.skeletonImporter import SkeletonImporter
from pyjallib.ue5.skeletalMeshImporter import SkeletalMeshImporter
from pyjallib.ue5.disableInterchangeFrameWork import add_disabled_plugins_to_uproject

fbxPath = r"E:\DevStorage_root\DevStorage\Characters\NPC\Human\NonBinary\Animation\LayerUpper\Gesture\A_Nc_Human_N_LayerUpper_Gesture_DisgustGesture.fbx"
skeletonPath = r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx"

contentRootPrefix = r"D:\root\Omni\Content\Omni"
contentRootPrefix = pathAndFiles.ue5.contentRootPath
fbxRootPrefix = r"E:\DevStorage_root\DevStorage"
fbxRootPrefix = str(Path(pathAndFiles.p4.devStorage) / "DevStorage")

testImporter = AnimationImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

result = testImporter.import_animation(fbxPath, skeletonPath)
print(result)
