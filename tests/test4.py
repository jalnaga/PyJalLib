import sys
import os

# 현재 스크립트의 디렉토리 path 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = os.path.abspath(os.path.join(current_dir, "..", "src"))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orvlib.p4Sync import P4Sync

orvP4 = P4Sync()
print(f"orvP4.devStorageP4: {orvP4.devStorageP4}")
print(f"orvP4.devStorageP4.connected: {orvP4.devStorageP4.connected}")
print(f"orvP4.devStorageP4.workspaceRoot: {orvP4.devStorageP4.workspaceRoot}")
print(f"orvP4.omniP4: {orvP4.omniP4}")
print(f"orvP4.omniP4.connected: {orvP4.omniP4.connected}")
print(f"orvP4.omniP4.workspaceRoot: {orvP4.omniP4.workspaceRoot}")

orvP4.devStorageP4.create_change_list("Test")
orvP4.omniP4.create_change_list("Test")

orvP4.devStorageP4.disconnect()
orvP4.omniP4.disconnect()
print(f"orvP4.devStorageP4.connected: {orvP4.devStorageP4.connected}")
print(f"orvP4.omniP4.connected: {orvP4.omniP4.connected}")

orvP4.devStorageP4.create_change_list("Test")
orvP4.omniP4.create_change_list("Test")