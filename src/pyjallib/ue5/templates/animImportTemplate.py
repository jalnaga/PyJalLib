import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = '{inExtPackagePath}'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

import pyjallib
from pyjallib.ue5.inUnreal.animationImporter import AnimationImporter

fbxPath = '{inAnimFbxPath}'
skeletonPath = '{inSkeletonFbxPath}'

contentRootPrefix = '{inContentRootPrefix}'
fbxRootPrefix = '{inFbxRootPrefix}'

animImporter = AnimationImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

result = animImporter.import_animation(fbxPath, skeletonPath)