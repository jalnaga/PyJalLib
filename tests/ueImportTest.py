import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 추가 (PyJalLib 디렉토리)
project_root = r"E:\DevStorage_root\DevStorage\ExtPythonPackage\.venv\Lib\site-packages"

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 새로운 pyjallib.ue5 구조 사용
from pyjallib.ue5 import add_disabled_plugins_to_uproject, TemplateProcessor
from orvlib import pathAndFiles

# 프로젝트 파일에 플러그인 비활성화 적용
omniProjectPath = pathAndFiles.ue5.projectPath
tempOmniProjectPath = add_disabled_plugins_to_uproject(omniProjectPath)

# TemplateProcessor 인스턴스 생성 - 전통적인 방식
templateProcessor = TemplateProcessor()

# 출력 스크립트 경로
animImportScriptPath = Path(__file__).parent / "animImportScript.py"

# 템플릿 데이터 준비
templateData = {
    "inExtPackagePath": project_root,
    "inAnimFbxPath": r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\GumhoDistrictBully\Male\Animation\BattleFist\Hit\A_Nm_GHDtBully_M_BattleFist_Hit.fbx",
    "inSkeletonFbxPath": r"E:\DevStorage_root\DevStorage\Characters\Shared\Human\Male\Mesh\BaseSkeleton\SK_Sh_Human_M_BaseSkeleton.fbx",
    "inContentRootPrefix": pathAndFiles.ue5.contentRootPath,
    "inFbxRootPrefix": str(Path(pathAndFiles.p4.devStorage) / "DevStorage")
}

# 새로운 방식: 타입별 특화 메서드 사용 (기존 8줄 → 1줄!)
templateProcessor.process_animation_import_template(
    inTemplateData=templateData,
    inOutputPath=str(animImportScriptPath)
)

# UE5 실행
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

# 보너스: 모듈 상태 정보 출력
print("\n=== PyJalLib UE5 모듈 상태 ===")
from pyjallib.ue5 import get_module_status, is_ue5_available

print(f"UE5 사용 가능: {is_ue5_available()}")
status = get_module_status()
print(f"사용 가능한 모듈: {status['available_modules']}")

