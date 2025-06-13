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

from pyjallib.max.header import get_pyjallibmaxheader

testJal = get_pyjallibmaxheader()

selObjs = rt.getCurrentSelection()

foundObjs = testJal.anim.find_animated_nodes(selObjs)

testJal.anim.load_animation(selObjs, r"C:\Users\Admin\Desktop\test.xaf")
