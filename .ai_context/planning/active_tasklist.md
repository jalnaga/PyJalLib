# Active Task List: Logger loguru 리팩토링

## 작업 항목

- [ ] 1. loguru 패키지 추가 (`uv add loguru`)
- [ ] 2. `pyjallib/logger.py` 새로 작성 (loguru 기반 Logger 클래스)
- [ ] 3. `pyjallib/ue5/logger.py` 새로 작성 (UE5Logger 클래스, Logger 상속)
- [ ] 4. `pyjallib/ue5/__init__.py` 수정 (전역 인스턴스/함수 제거, UE5Logger 클래스 export)
- [ ] 5. `pyjallib/ue5/templateProcessor.py` 수정 (모듈 레벨 logger 인스턴스 생성)
- [ ] 6. `pyjallib/ue5/disableInterchangeFrameWork.py` 수정 (모듈 레벨 logger 인스턴스 생성)
- [ ] 7. `pyjallib/ue5/inUnreal/baseImporter.py` 수정 (모듈 레벨 logger 인스턴스 생성)
- [ ] 8. `pyjallib/ue5/inUnreal/animationImporter.py` 수정 (모듈 레벨 logger 인스턴스 생성)
- [ ] 9. `pyjallib/ue5/inUnreal/skeletonImporter.py` 수정 (모듈 레벨 logger 인스턴스 생성)
- [ ] 10. `pyjallib/ue5/inUnreal/skeletalMeshImporter.py` 수정 (모듈 레벨 logger 인스턴스 생성)
