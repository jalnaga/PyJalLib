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
from pyjallib.p4module import P4Module

testP4 = P4Module()
testP4.connect("DongseokKim_DevStorage")
pendingList = testP4.get_pending_change_list()
print(pendingList[0])
print(testP4.edit_change_list(pendingList[0]["Change"], description="test"))
print(testP4.revert_change_list(pendingList[0]["Change"]))