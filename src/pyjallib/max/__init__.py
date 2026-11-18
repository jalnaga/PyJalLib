"""3ds Max 도구를 속성 접근 시 로드하여 순수 모듈의 콘솔 사용을 지원한다."""

import importlib
from typing import Any

_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "Header": ('pyjallib.max.header', 'Header'),
    "Name": ('pyjallib.max.name', 'Name'),
    "Anim": ('pyjallib.max.anim', 'Anim'),
    "Helper": ('pyjallib.max.helper', 'Helper'),
    "Constraint": ('pyjallib.max.constraint', 'Constraint'),
    "Bone": ('pyjallib.max.bone', 'Bone'),
    "Mirror": ('pyjallib.max.mirror', 'Mirror'),
    "Layer": ('pyjallib.max.layer', 'Layer'),
    "Align": ('pyjallib.max.align', 'Align'),
    "Select": ('pyjallib.max.select', 'Select'),
    "Link": ('pyjallib.max.link', 'Link'),
    "Bip": ('pyjallib.max.bip', 'Bip'),
    "Skin": ('pyjallib.max.skin', 'Skin'),
    "Skeleton": ('pyjallib.max.skeleton', 'Skeleton'),
    "Morph": ('pyjallib.max.morph', 'Morph'),
    "Attribute": ('pyjallib.max.attribute', 'Attribute'),
    "Polygon": ('pyjallib.max.polygon', 'Polygon'),
    "uvMask": ('pyjallib.max.uvMask', None),
    "clipMesh": ('pyjallib.max.clipMesh', None),
    "BoneChain": ('pyjallib.max.rig.boneChain', 'BoneChain'),
    "TwistBone": ('pyjallib.max.rig.twistBone', 'TwistBone'),
    "GroinBone": ('pyjallib.max.rig.groinBone', 'GroinBone'),
    "AutoClavicle": ('pyjallib.max.rig.autoClavicle', 'AutoClavicle'),
    "Shoulder": ('pyjallib.max.rig.shoulder', 'Shoulder'),
    "Armpit": ('pyjallib.max.rig.armpit', 'Armpit'),
    "Chest": ('pyjallib.max.rig.chest', 'Chest'),
    "VolumeBone": ('pyjallib.max.rig.volumeBone', 'VolumeBone'),
    "Elbow": ('pyjallib.max.rig.elbow', 'Elbow'),
    "Wrist": ('pyjallib.max.rig.wrist', 'Wrist'),
    "Ankle": ('pyjallib.max.rig.ankle', 'Ankle'),
    "Inguinal": ('pyjallib.max.rig.inguinal', 'Inguinal'),
    "KneeBone": ('pyjallib.max.rig.kneeBone', 'KneeBone'),
    "Hip": ('pyjallib.max.rig.hip', 'Hip'),
    "JacketPanel": ('pyjallib.max.rig.jacketPanel', 'JacketPanel'),
    "UE5Skeleton": ('pyjallib.max.ue5Skeleton', 'UE5Skeleton'),
    "RootMotion": ('pyjallib.max.rootMotion', 'RootMotion'),
    "Dependent": ('pyjallib.max.dependent', 'Dependent'),
    "NodeCollectPolicy": ('pyjallib.max.nodeCollectPolicy', 'NodeCollectPolicy'),
    "NodeCollectResolver": ('pyjallib.max.nodeCollectResolver', 'NodeCollectResolver'),
    "build_policy": ('pyjallib.max.nodeCollectResolver', 'build_policy'),
    "MissingAsset": ('pyjallib.max.missingAssetResolver', 'MissingAsset'),
    "CheckViewport": ('pyjallib.max.checkViewport', 'CheckViewport'),
    "CheckLayer": ('pyjallib.max.checkLayer', 'CheckLayer'),
    "CheckMaterial": ('pyjallib.max.checkMaterial', 'CheckMaterial'),
    "CheckObject": ('pyjallib.max.checkObject', 'CheckObject'),
    "FBXHandler": ('pyjallib.max.fbxHandler', 'FBXHandler'),
    "ToolManager": ('pyjallib.max.toolManager', 'ToolManager'),
    "Progress": ('pyjallib.max.progress', 'Progress'),
    "Container": ('pyjallib.max.ui.Container', 'Container'),
    "ToolState": ('pyjallib.max.ui.toolState', 'ToolState'),
}

__all__ = list(_LAZY_IMPORTS)


def __getattr__(inName: str) -> Any:
    """기존 공개 심볼을 처음 접근할 때 불러오고 캐시한다."""
    if inName not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {inName!r}")
    modulePath, symbolName = _LAZY_IMPORTS[inName]
    module = importlib.import_module(modulePath)
    value = module if symbolName is None else getattr(module, symbolName)
    globals()[inName] = value
    return value


def __dir__() -> list[str]:
    """지연 로딩하는 공개 심볼도 자동완성 목록에 포함한다."""
    return sorted(set(globals()) | set(__all__))
