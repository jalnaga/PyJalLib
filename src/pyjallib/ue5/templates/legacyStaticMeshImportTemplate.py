import sys
import unreal

# inUnreal 디렉토리를 직접 sys.path에 추가 (pyjallib 패키지 전체를 로드하지 않음)
extPackagePath = r'{inExtPackagePath}'
inUnrealPath = extPackagePath + r'/pyjallib/ue5/inUnreal'

if inUnrealPath not in sys.path:
    sys.path.insert(0, inUnrealPath)

from legacyBaseImporter import LegacyBaseImporter
from legacyStaticMeshImporter import LegacyStaticMeshImporter
from pathUtils import ensure_directory_exists, checkout_or_add_file, open_for_source_control_checked
from importResultWriter import write_import_result

# 결과 JSON 경로 (선택) - 비어 있으면 기록을 생략한다 (구 툴 하위호환)
resultJsonPath = r'{inResultJsonPath}'

# Material Instance의 Parent Material (/Game/... Content 경로)
parentMaterialPath = r'{inParentMaterialContentPath}'

# 슬롯 데이터 - 호출자가 파이썬 리터럴 코드로 넘긴다.
# slots = [
#     {
#         'slotName': str, 'fbxPath': str, 'meshDestPath': str, 'assetName': str,
#         'textures': [{'sourcePath': str, 'destPath': str, 'assetName': str}, ...],
#         'materialDestPath': str, 'materialNames': [str, ...],
#     },
#     ...
# ]
slots = []  # 아래 자리표시자 치환이 실제 슬롯 리스트로 덮어쓴다
{inSlotsData}  # noqa: F821

# 에디터 안에서는 체인지리스트를 만들거나 옮길 수 없다(UE5 Python API 부재).
# 임포트한 에셋을 default 체인지리스트에 열어두기만 하고, 연 파일 절대경로를
# 결과 JSON으로 남겨 툴 프로세스가 이름 붙은 CL로 모으게 한다.
importResults = []

# ========================================
# Static Mesh 임포트
# ========================================
meshResults = []
for slot in slots:
    try:
        unreal.log(f"[legacyStaticMeshImport] Static Mesh 임포트 시작: {slot['slotName']}")

        # 대상 디렉토리 생성 보장
        ensure_directory_exists(slot['meshDestPath'])

        # prefix 자동 추론
        contentRootPrefix, fbxRootPrefix = LegacyBaseImporter.infer_prefixes_from_paths(
            slot['meshDestPath'], slot['fbxPath']
        )

        # 임포터 초기화 및 실행
        importer = LegacyStaticMeshImporter(
            inContentRootPrefix=contentRootPrefix,
            inFbxRootPrefix=fbxRootPrefix
        )

        assetNameArg = slot['assetName'] if slot['assetName'] else None
        result = importer.import_static_mesh(slot['fbxPath'], inAssetName=assetNameArg)
        importResults.append(result)

        meshResults.append({'slot': slot['slotName'], 'success': True})
        unreal.log(f"[legacyStaticMeshImport] Static Mesh 임포트 성공: {slot['slotName']}")
    except Exception as e:
        meshResults.append({'slot': slot['slotName'], 'success': False, 'error': str(e)})
        unreal.log_error(f"[legacyStaticMeshImport] Static Mesh 임포트 실패: {slot['slotName']} - {e}")

# ========================================
# Texture 임포트
# ========================================
texResults = []
for slot in slots:
    for tex in slot['textures']:
        try:
            unreal.log(f"[legacyStaticMeshImport] Texture 임포트 시작: {tex['assetName']}")

            # 대상 디렉토리 생성 보장
            ensure_directory_exists(tex['destPath'])

            texAssetPath = f"{tex['destPath']}/{tex['assetName']}"

            # 기존 에셋이면 임포트 전에 체크아웃해 쓰기 권한을 확보한다
            checkout_or_add_file(texAssetPath)

            task = unreal.AssetImportTask()
            task.automated = True
            task.destination_path = tex['destPath']
            task.filename = tex['sourcePath']
            task.destination_name = tex['assetName']
            task.replace_existing = True
            task.save = True

            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

            # 임포트 결과를 소스 컨트롤에 열고 연 파일 경로를 수집한다.
            # 체크아웃 실패분은 연 파일 목록에서 빠지고 FailedFiles로 보고된다 -
            # 열리지 않은 파일을 CL로 옮기려다 부분 실패가 나는 것을 막는다.
            scResult = open_for_source_control_checked([texAssetPath])
            importResults.append({'OpenedFiles': scResult['opened'], 'FailedFiles': scResult['failed']})

            texResults.append({'texture': tex['assetName'], 'success': True})
            unreal.log(f"[legacyStaticMeshImport] Texture 임포트 성공: {tex['assetName']}")
        except Exception as e:
            texResults.append({'texture': tex['assetName'], 'success': False, 'error': str(e)})
            unreal.log_error(f"[legacyStaticMeshImport] Texture 임포트 실패: {tex['assetName']} - {e}")

# ========================================
# Material Instance 생성
# ========================================
matResults = []

# Parent Material 로드
parentMaterial = unreal.EditorAssetLibrary.load_asset(parentMaterialPath)
if parentMaterial is None:
    unreal.log_error(f"[legacyStaticMeshImport] Parent Material 로드 실패: {parentMaterialPath}")
else:
    factory = unreal.MaterialInstanceConstantFactoryNew()
    assetTools = unreal.AssetToolsHelpers.get_asset_tools()

    for slot in slots:
        for matName in slot['materialNames']:
            try:
                unreal.log(f"[legacyStaticMeshImport] Material Instance 생성 시작: {matName}")

                # 대상 디렉토리 생성 보장
                ensure_directory_exists(slot['materialDestPath'])

                assetPath = f"{slot['materialDestPath']}/{matName}"

                # 기존 에셋 존재 시 체크아웃 후 로드, 없으면 신규 생성
                if unreal.EditorAssetLibrary.does_asset_exist(assetPath):
                    unreal.log(f"[legacyStaticMeshImport] 기존 Material Instance 발견, 덮어쓰기: {matName}")
                    checkout_or_add_file(assetPath)
                    mi = unreal.EditorAssetLibrary.load_asset(assetPath)
                else:
                    mi = assetTools.create_asset(matName, slot['materialDestPath'], unreal.MaterialInstanceConstant, factory)

                if mi is None:
                    matResults.append({'material': matName, 'success': False, 'error': 'create_asset returned None'})
                    unreal.log_error(f"[legacyStaticMeshImport] Material Instance 생성 실패: {matName}")
                    continue

                # Parent Material 설정
                mi.set_editor_property("parent", parentMaterial)

                # 저장
                unreal.EditorAssetLibrary.save_asset(assetPath)

                # 신규 생성분은 add, 기존분은 edit으로 열고 연 파일 경로를 수집한다.
                # 체크아웃 실패분은 FailedFiles로 갈라 보고한다.
                scResult = open_for_source_control_checked([assetPath])
                importResults.append({'OpenedFiles': scResult['opened'], 'FailedFiles': scResult['failed']})

                matResults.append({'material': matName, 'success': True})
                unreal.log(f"[legacyStaticMeshImport] Material Instance 생성 성공: {matName}")
            except Exception as e:
                matResults.append({'material': matName, 'success': False, 'error': str(e)})
                unreal.log_error(f"[legacyStaticMeshImport] Material Instance 생성 실패: {matName} - {e}")

# ========================================
# 결과 요약
# ========================================
meshSuccess = sum(1 for r in meshResults if r['success'])
meshFail = sum(1 for r in meshResults if not r['success'])
texSuccess = sum(1 for r in texResults if r['success'])
texFail = sum(1 for r in texResults if not r['success'])
matSuccess = sum(1 for r in matResults if r['success'])
matFail = sum(1 for r in matResults if not r['success'])

unreal.log(f"[legacyStaticMeshImport] 임포트 완료 - Mesh: {meshSuccess} 성공 / {meshFail} 실패, Texture: {texSuccess} 성공 / {texFail} 실패, Material: {matSuccess} 성공 / {matFail} 실패")

# 연 파일 목록을 결과 JSON으로 남긴다 (툴 프로세스가 CL 이동에 사용).
# 개별 항목 실패는 위에서 격리했으므로, 여기서는 전체 실패 여부만 기록한다.
importFailed = (meshFail + texFail + matFail) > 0
write_import_result(
    resultJsonPath,
    importResults,
    inSuccess=not importFailed,
    inError=f"실패 - Mesh {meshFail} / Texture {texFail} / Material {matFail}" if importFailed else None,
)
