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

tempJal = pyjallib.max.header.Header()

selObjs = rt.getCurrentSelection()

clavicle = tempJal.bip.get_grouped_nodes(selObjs[0], "lArm")[0]
upperArm = tempJal.bip.get_grouped_nodes(selObjs[0], "lArm")[1]

print(clavicle, upperArm)

tempJal.autoClavicle.create_bones(clavicle, upperArm, liftScale=0.8)