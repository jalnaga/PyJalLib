import sys
import os

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib
pyjallib.reload_modules()

from pyjallib.ue5.animation_importer import AnimationImporter

testImporter = AnimationImporter(inContentRootPrefix=r"D:\root\Omni\Content\Omni", inFbxRootPrefix=r"E:\DevStorage_root\DevStorage")
result = testImporter.import_animation(inFbxFile=r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\BattleFist\Run\A_Nm_GHDtBully_M_BattleFist_Run.fbx", inFbxSkeletonPath=r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx")