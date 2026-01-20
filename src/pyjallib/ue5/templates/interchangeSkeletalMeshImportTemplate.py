import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
extPackagePath = r'{inExtPackagePath}'

if extPackagePath not in sys.path:
    sys.path.insert(0, extPackagePath)

import pyjallib
from pyjallib.ue5.inUnreal.interchangeSkeletalMeshImporter import InterchangeSkeletalMeshImporter

fbxPath = r'{inSkeletalMeshFbxPath}'
skeletonFbxPath = r'{inSkeletonFbxPath}'

contentRootPrefix = r'{inContentRootPrefix}'
fbxRootPrefix = r'{inFbxRootPrefix}'

skeletalMeshImporter = InterchangeSkeletalMeshImporter(inContentRootPrefix=contentRootPrefix, inFbxRootPrefix=fbxRootPrefix)

result = skeletalMeshImporter.import_skeletal_mesh(fbxPath, skeletonFbxPath)
