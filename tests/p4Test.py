import sys
import os

# 현재 스크립트의 디렉토리 path 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = os.path.abspath(os.path.join(current_dir, "..", "src"))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pyjallib
pyjallib.reload_modules()

import pyjallib
from pyjallib.perforce import Perforce

testP4 = Perforce()
testP4.connect("DongseokKim_Omni")
print(testP4.workspaceRoot)
testP4.disconnect()
testP4.connect("DongseokKim_DevStorage")
print(testP4.workspaceRoot)