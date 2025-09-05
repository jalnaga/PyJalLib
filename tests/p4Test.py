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

connectResult = testP4.connect("DongseokKim_DevStorage")
print(f"connectResult: {connectResult}")
print(f"  - connected: {testP4.connected}")
print(f"  - workspaceRoot: {testP4.workspaceRoot}")

result = testP4.create_change_list("Test")
print(f"result: {result}")

from orvlib.p4Sync import P4Sync

orvP4 = P4Sync()
print(f"orvP4: {orvP4}")
print(f"orvP4.devStorageP4: {orvP4.devStorageP4}")
print(f"orvP4.omniP4: {orvP4.omniP4}")