import sys
import os

# 현재 스크립트의 디렉토리 path 가져오기
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = os.path.abspath(os.path.join(current_dir, "..", "src"))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pymxs import runtime as rt
import pyjallib
pyjallib.reload_modules()

testJal = pyjallib.max.header.get_pyjallibmaxheader()

baseSkeletons = testJal.layer.get_nodes_by_layername("Rig")
ikBones = testJal.layer.get_nodes_by_layername("Rig_IK")

exportBones = baseSkeletons + ikBones

rt.clearSelection()
rt.select(exportBones)

testJal.fbx.export_selection(r"C:\Users\Admin\Desktop\test.fbx", inMatchAnimRange=True)