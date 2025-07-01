import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pyjallib.ue5.disableInterchangeFrameWork import add_disabled_plugins_to_uproject
from orvlib import pathAndFiles

omniProjectPath = pathAndFiles.ue5.projectPath
tempOmniProjectPath = add_disabled_plugins_to_uproject(omniProjectPath)

from pyjallib.ue5.templateProcessor import TemplateProcessor

# animImportTemplate.py 파일 경로를 가져오려면 다음과 같이 작성합니다
import importlib.util

# 모듈 경로 찾기
animImportTemplate_spec = importlib.util.find_spec("pyjallib.ue5.animImportTemplate")
animImportTemplate_path = animImportTemplate_spec.origin if animImportTemplate_spec else None

templateProcessor = TemplateProcessor()

animImportScriptPath = Path(__file__).parent / "animImportScript.py"

templateProcessor.process_template(
    inTemplatePath=animImportTemplate_path,
    inTemplateOutPath=animImportScriptPath,
    inTemplateData={
    "inExtPackagePath": project_root,
    "inAnimFbxPath": r"E:\DevStorage_root\DevStorage\Characters\NPC\Human\NonBinary\Animation\SittingSlumped\Transition\A_Nc_Human_N_SittingSlumped_Transition_HandOnHip.fbx",
    "inSkeletonFbxPath": r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx",
    "inContentRootPrefix": pathAndFiles.ue5.contentRootPath,
    "inFbxRootPrefix": str(Path(pathAndFiles.p4.devStorage) / "DevStorage")
    }
)

cmd = f'{pathAndFiles.ue5.editorPath} "{tempOmniProjectPath}" -run=pythonscript -script="{animImportScriptPath}"'

import subprocess
subprocess.run(cmd, shell=True)

# 임시 파일 삭제
try:
    # 임시 프로젝트 파일 삭제
    if os.path.exists(tempOmniProjectPath):
        os.remove(tempOmniProjectPath)
        print(f"임시 프로젝트 파일이 삭제되었습니다: {tempOmniProjectPath}")
    
    # 애니메이션 임포트 스크립트 파일 삭제
    if os.path.exists(animImportScriptPath):
        os.remove(animImportScriptPath)
        print(f"애니메이션 임포트 스크립트 파일이 삭제되었습니다: {animImportScriptPath}")
except Exception as e:
    print(f"파일 삭제 중 오류가 발생했습니다: {e}")

