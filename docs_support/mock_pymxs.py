import sys
import types

pymxs = types.ModuleType("pymxs")

# 모듈 수준에서 필요한 함수들 추가
pymxs.attime = lambda *args, **kwargs: None
pymxs.animate = lambda *args, **kwargs: None
pymxs.undo = types.SimpleNamespace(
    begin=lambda *a, **kw: None,
    end=lambda *a, **kw: None
)

# pymxs.runtime도 여전히 있어야 함
pymxs.runtime = types.SimpleNamespace()

sys.modules["pymxs"] = pymxs

