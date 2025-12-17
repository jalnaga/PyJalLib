# Facade Pattern Reference

## 구조

```
MainFacade
├── _sharedData: dict        ← 공유 상태
├── configPath: str
├── subModule1: SubModule1   ← self 참조 전달
├── subModule2: SubModule2
└── subModule3: SubModule3
```

---

## 메인 Facade 클래스

```python
class MainFacade:
    def __init__(self, inConfigPath: str = None):
        self.configPath = inConfigPath
        self._sharedData = {}
        
        # 서브 모듈 초기화 (의존성 주입)
        self.subModule1 = SubModule1(self)
        self.subModule2 = SubModule2(self)
```

---

## 서브 모듈 클래스

```python
class SubModule1:
    def __init__(self, inParent: "MainFacade"):
        self._parent = inParent
    
    @property
    def _data(self) -> dict:
        return self._parent._sharedData
    
    def some_method(self, inParam: str) -> bool:
        self._data["key"] = inParam
        return True
```

---

## 파일 구조

```
src/myPackage/
├── __init__.py       # from .mainFacade import MainFacade
├── mainFacade.py     # MainFacade 클래스
├── subModule1.py     # SubModule1 클래스
└── subModule2.py     # SubModule2 클래스
```

---

## 사용 예시

```python
facade = MainFacade(inConfigPath="config.json")
facade.subModule1.some_method("value")
facade.subModule2.another_method()
```
