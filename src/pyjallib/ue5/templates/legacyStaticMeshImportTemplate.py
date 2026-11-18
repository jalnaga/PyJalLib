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

# Material Instance의 전역 Parent Material (/Game/... Content 경로).
# 슬롯 dict에 'parentMaterialPath'가 없거나 빈 문자열이면 이 경로를 쓴다.
parentMaterialPath = r'{inParentMaterialContentPath}'

# 슬롯 데이터 - 호출자가 파이썬 리터럴 코드로 넘긴다.
# slots = [
#     {
#         'slotName': str, 'fbxPath': str, 'meshDestPath': str, 'assetName': str,
#         'textures': [
#             {
#                 'sourcePath': str, 'destPath': str, 'assetName': str,
#                 # 선택 - 임포트 직후 적용할 텍스쳐 설정. 있는 키만 적용한다.
#                 # enum 값은 unreal enum 멤버 이름 문자열, srgb는 bool.
#                 'settings': {'compressionSettings': 'TC_MASKS',
#                              'lodGroup': 'TEXTUREGROUP_CHARACTER_SPECULAR',
#                              'srgb': False, 'addressX': 'TA_WRAP', 'addressY': 'TA_WRAP'},
#             },
#             ...
#         ],
#         'materialDestPath': str, 'materialNames': [str, ...],
#         'parentMaterialPath': str,  # 선택 - 이 슬롯 MI의 Parent Material (/Game/...)
#         # 선택 - MI 이름별 텍스쳐 파라미터 지정. materialNames에 없는 MI 키는 무시한다.
#         'materialTextureParams': {
#             '<MI 이름>': [{'parameterName': str, 'textureAssetPath': '/Game/...'}, ...],
#         },
#     },
#     ...
# ]
slots = []  # 아래 자리표시자 치환이 실제 슬롯 리스트로 덮어쓴다
{inSlotsData}  # noqa: F821

# 에디터 안에서는 체인지리스트를 만들거나 옮길 수 없다(UE5 Python API 부재).
# 임포트한 에셋을 default 체인지리스트에 열어두기만 하고, 연 파일 절대경로를
# 결과 JSON으로 남겨 툴 프로세스가 이름 붙은 CL로 모으게 한다.
importResults = []

# 텍스쳐 에셋은 경로별로 한 번만 로드한다(설정 적용·MI 파라미터 지정 공용).
# 로드 실패(None)도 캐시해 재시도·중복 로그를 막는다.
textureAssetCache = {}


def load_texture_asset(inPath):
    """텍스쳐 에셋을 경로별 캐시를 거쳐 로드한다. 실패하면 None."""
    if inPath not in textureAssetCache:
        loaded = None
        try:
            loaded = unreal.EditorAssetLibrary.load_asset(inPath)
        except Exception as e:
            unreal.log_error(f"[legacyStaticMeshImport] 텍스쳐 로드 예외: {inPath} - {e}")
        textureAssetCache[inPath] = loaded
    return textureAssetCache[inPath]


# 텍스쳐 설정 계약 키 → (Texture 프로퍼티 이름, unreal enum 클래스 이름 또는 None=bool)
TEXTURE_SETTING_SPECS = (
    ('compressionSettings', 'compression_settings', 'TextureCompressionSettings'),
    ('lodGroup', 'lod_group', 'TextureGroup'),
    ('srgb', 'srgb', None),
    ('addressX', 'address_x', 'TextureAddress'),
    ('addressY', 'address_y', 'TextureAddress'),
)


def resolve_texture_setting_value(inKey, inEnumClassName, inValue):
    """계약 값을 프로퍼티에 쓸 값으로 바꾼다.

    enum은 이름 문자열을 해당 unreal enum에서 getattr로 찾는다. 다른 enum의 멤버
    이름은 그 enum에 없으므로 거절된다. 메서드 등 멤버가 아닌 속성도 거절한다.

    Returns:
        (값, None) 또는 (None, 오류 사유)
    """
    if inEnumClassName is None:
        if not isinstance(inValue, bool):
            return None, f"{inKey}: bool이 아닌 값 {inValue!r}"
        return inValue, None

    if not isinstance(inValue, str) or not inValue or inValue.startswith('_'):
        return None, f"{inKey}: 잘못된 {inEnumClassName} 이름 {inValue!r}"
    enumClass = getattr(unreal, inEnumClassName, None)
    if enumClass is None:
        return None, f"{inKey}: unreal.{inEnumClassName}을(를) 찾을 수 없음"
    member = getattr(enumClass, inValue, None)
    if member is None or callable(member):
        return None, f"{inKey}: 알 수 없는 {inEnumClassName} 이름 '{inValue}'"
    return member, None


def apply_texture_settings(inTexAssetPath, inSettings):
    """임포트한 텍스쳐에 설정을 적용하고 되읽어 확인한 뒤 저장한다.

    UE5 쓰기는 조용히 무시될 수 있으므로 성공 판정은 되읽기로 한다.
    값 해석을 모두 마친 뒤에 쓰기 시작해, 잘못된 이름이 하나라도 있으면 아무것도
    쓰지 않는다. 되확인이 불일치하면 부분 적용 상태를 저장하지 않는다.

    Returns:
        None(성공) 또는 오류 사유 문자열
    """
    unknownKeys = sorted(k for k in inSettings if k not in {s[0] for s in TEXTURE_SETTING_SPECS})
    if unknownKeys:
        unreal.log_warning(f"[legacyStaticMeshImport] 알 수 없는 텍스쳐 설정 키 무시: {inTexAssetPath} - {unknownKeys}")

    # 1) 값 해석 - 실패가 있으면 쓰기 전에 중단한다
    plan = []
    resolveErrors = []
    for key, propName, enumClassName in TEXTURE_SETTING_SPECS:
        if key not in inSettings:
            continue
        value, error = resolve_texture_setting_value(key, enumClassName, inSettings[key])
        if error:
            resolveErrors.append(error)
        else:
            plan.append((key, propName, value))
    if resolveErrors:
        return "텍스쳐 설정 값 오류: " + "; ".join(resolveErrors)
    if not plan:
        return None

    # 2) 로드
    texture = load_texture_asset(inTexAssetPath)
    if texture is None:
        return f"텍스쳐 에셋 로드 실패: {inTexAssetPath}"

    # 3) 쓰기 → 되읽기
    try:
        for _key, propName, value in plan:
            texture.set_editor_property(propName, value)

        mismatches = []
        for key, propName, value in plan:
            actual = texture.get_editor_property(propName)
            if actual != value:
                mismatches.append(f"{key}({propName}) 기대 {value} / 실제 {actual}")
        if mismatches:
            return "텍스쳐 설정 되확인 불일치: " + "; ".join(mismatches)

        # 4) 저장 - 반환값으로 판정한다
        if not unreal.EditorAssetLibrary.save_asset(inTexAssetPath, only_if_is_dirty=False):
            return f"텍스쳐 설정 저장 실패: {inTexAssetPath}"
    except Exception as e:
        return f"텍스쳐 설정 적용 예외: {e}"
    return None

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

            # 선택 설정 적용. 실패해도 임포트 자체는 디스크에 저장됐으므로
            # 소스 컨트롤 열기는 그대로 하고 결과만 실패로 기록한다.
            settingsError = None
            texSettings = tex.get('settings')
            if texSettings:
                settingsError = apply_texture_settings(texAssetPath, texSettings)

            # 임포트 결과를 소스 컨트롤에 열고 연 파일 경로를 수집한다.
            # 체크아웃 실패분은 연 파일 목록에서 빠지고 FailedFiles로 보고된다 -
            # 열리지 않은 파일을 CL로 옮기려다 부분 실패가 나는 것을 막는다.
            scResult = open_for_source_control_checked([texAssetPath])
            importResults.append({'OpenedFiles': scResult['opened'], 'FailedFiles': scResult['failed']})

            if settingsError:
                texResults.append({'texture': tex['assetName'], 'success': False, 'error': settingsError})
                unreal.log_error(f"[legacyStaticMeshImport] Texture 설정 실패: {tex['assetName']} - {settingsError}")
                continue

            texResults.append({'texture': tex['assetName'], 'success': True})
            unreal.log(f"[legacyStaticMeshImport] Texture 임포트 성공: {tex['assetName']}")
        except Exception as e:
            texResults.append({'texture': tex['assetName'], 'success': False, 'error': str(e)})
            unreal.log_error(f"[legacyStaticMeshImport] Texture 임포트 실패: {tex['assetName']} - {e}")

# ========================================
# Material Instance 생성
# ========================================
matResults = []

# 같은 부모 경로는 한 번만 로드한다. 로드 실패(None)도 캐시해 재시도·중복 로그를 막는다.
parentMaterialCache = {}


def get_slot_parent_material_path(inSlot):
    """슬롯의 Parent Material 경로. 키가 없거나 빈 문자열이면 전역 경로를 쓴다."""
    return inSlot.get('parentMaterialPath') or parentMaterialPath


def load_parent_material(inPath):
    """Parent Material을 경로별 캐시를 거쳐 로드한다. 실패하면 None."""
    if inPath not in parentMaterialCache:
        loaded = unreal.EditorAssetLibrary.load_asset(inPath)
        if loaded is None:
            unreal.log_error(f"[legacyStaticMeshImport] Parent Material 로드 실패: {inPath}")
        parentMaterialCache[inPath] = loaded
    return parentMaterialCache[inPath]


# 부모 머티리얼별 텍스쳐 파라미터 이름 집합(str). 조회 실패는 None으로 캐시한다.
parentTextureParamNamesCache = {}


def get_parent_texture_param_names(inParentPath, inParentMaterial):
    """부모 머티리얼의 텍스쳐 파라미터 이름 집합을 부모별 캐시를 거쳐 얻는다. 실패하면 None.

    unreal.Name은 str이 아니므로 str로 바꿔 담는다.
    """
    if inParentPath not in parentTextureParamNamesCache:
        names = None
        try:
            names = {str(n) for n in unreal.MaterialEditingLibrary.get_texture_parameter_names(inParentMaterial)}
        except Exception as e:
            unreal.log_error(f"[legacyStaticMeshImport] 부모 텍스쳐 파라미터 목록 조회 실패: {inParentPath} - {e}")
        parentTextureParamNamesCache[inParentPath] = names
    return parentTextureParamNamesCache[inParentPath]


def is_same_asset(inActual, inExpected):
    """되읽은 에셋이 지정한 에셋과 같은지 비교한다(객체 비교 후 경로 비교)."""
    if inActual is None:
        return False
    if inActual == inExpected:
        return True
    try:
        return inActual.get_path_name() == inExpected.get_path_name()
    except Exception:
        return False


def assign_material_texture_params(inMi, inParentPath, inParentMaterial, inParams):
    """MI의 텍스쳐 파라미터에 텍스쳐를 지정하고 되읽어 확인한다.

    부모 머티리얼에 없는 이름은 부모가 그 텍스쳐를 쓰지 않는 정상 경우이므로 실패가
    아니라 경고로 남기고 쓰지 않는다(쓰면 쓰이지 않는 오버라이드만 생긴다). 성공 판정은
    지정 함수의 반환값이 아니라 되읽기 결과로만 한다. 한 파라미터의 실패가 다른
    파라미터 지정을 막지 않는다. 기존 오버라이드를 지우지 않는다.

    Returns:
        실패 목록 [(파라미터 이름, 사유), ...]
    """
    mel = unreal.MaterialEditingLibrary
    failures = []
    parentNames = get_parent_texture_param_names(inParentPath, inParentMaterial)

    for param in inParams:
        paramName = param.get('parameterName')
        texturePath = param.get('textureAssetPath')
        if not paramName:
            failures.append((str(paramName), "parameterName 누락"))
            continue
        if parentNames is None:
            failures.append((paramName, f"부모 텍스쳐 파라미터 목록 조회 실패 ({inParentPath})"))
            continue
        if paramName not in parentNames:
            unreal.log_warning(
                f"[legacyStaticMeshImport] 부모 머티리얼에 텍스쳐 파라미터 없음, 지정 건너뜀: "
                f"{inMi.get_path_name()} - {paramName} (부모 {inParentPath})"
            )
            continue
        texture = load_texture_asset(texturePath) if texturePath else None
        if texture is None:
            failures.append((paramName, f"텍스쳐 로드 실패 ({texturePath})"))
            continue
        try:
            # 반환값은 판정에 쓰지 않는다. 엔진 MaterialEditingLibrary.cpp:1187
            # SetMaterialInstanceTextureParameterValue는 값을 쓴 뒤에도 bResult를 갱신하지 않아
            # 항상 False를 돌려준다(UE 5.7.4 실기 UAT 확인). 되읽기 결과만으로 판정한다.
            mel.set_material_instance_texture_parameter_value(inMi, paramName, texture)
            actual = mel.get_material_instance_texture_parameter_value(inMi, paramName)
        except Exception as e:
            failures.append((paramName, f"지정 예외: {e}"))
            continue
        if not is_same_asset(actual, texture):
            failures.append((paramName, f"되확인 불일치 (기대 {texturePath})"))

    return failures


factory = unreal.MaterialInstanceConstantFactoryNew()
assetTools = unreal.AssetToolsHelpers.get_asset_tools()

for slot in slots:
    slotParentPath = get_slot_parent_material_path(slot)
    parentMaterial = load_parent_material(slotParentPath)
    slotTextureParams = slot.get('materialTextureParams') or {}

    for matName in slot['materialNames']:
        # 부모를 못 불러온 슬롯은 그 슬롯의 MI만 실패로 기록하고 다른 슬롯은 계속 처리한다
        if parentMaterial is None:
            matResults.append({
                'material': matName,
                'success': False,
                'error': f"Parent Material 로드 실패: {slotParentPath}",
            })
            unreal.log_error(f"[legacyStaticMeshImport] Material Instance 생성 실패: {matName} - Parent Material 로드 실패: {slotParentPath}")
            continue

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

            # Parent Material 설정 (기존 MI도 슬롯의 부모로 덮어쓴다)
            mi.set_editor_property("parent", parentMaterial)

            # 선택 - 텍스쳐 파라미터 지정. 일부가 실패해도 성공한 지정과 부모 설정은
            # 저장·소스 컨트롤 열기를 유지하고 결과만 실패로 기록한다.
            paramFailures = []
            miTextureParams = slotTextureParams.get(matName) or []
            if miTextureParams:
                paramFailures = assign_material_texture_params(mi, slotParentPath, parentMaterial, miTextureParams)
                unreal.MaterialEditingLibrary.update_material_instance(mi)

            # 저장
            unreal.EditorAssetLibrary.save_asset(assetPath)

            # 신규 생성분은 add, 기존분은 edit으로 열고 연 파일 경로를 수집한다.
            # 체크아웃 실패분은 FailedFiles로 갈라 보고한다.
            scResult = open_for_source_control_checked([assetPath])
            importResults.append({'OpenedFiles': scResult['opened'], 'FailedFiles': scResult['failed']})

            if paramFailures:
                paramError = "텍스쳐 파라미터 지정 실패: " + "; ".join(
                    f"{name} - {reason}" for name, reason in paramFailures
                )
                matResults.append({'material': matName, 'success': False, 'error': paramError})
                unreal.log_error(f"[legacyStaticMeshImport] Material Instance 텍스쳐 파라미터 실패: {matName} - {paramError}")
                continue

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
