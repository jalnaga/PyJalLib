# PyJalLib Mocap Module PRD
## Product Requirements Document

**프로젝트명**: PyJalLib mocap.py 모듈 개발  
**버전**: 1.0  
**작성일**: 2025년 1월 18일  
**작성자**: Development Team  

---

## 1. 프로젝트 개요

### 1.1 목적
BIPPY MaxScript의 핵심 기능을 분석하여 PyJalLib에 `mocap.py` 모듈을 추가하고, FBX 모션 캡처 데이터를 3DS Max Biped 시스템으로 자동 변환하는 Python 기반 솔루션을 제공한다.

### 1.2 배경
- 기존 BIPPY MaxScript는 FBX → Biped 변환에 효과적이지만 MaxScript로 제한됨
- PyJalLib의 기존 아키텍처와 통합된 Python 솔루션 필요
- 모션 캡처 워크플로우의 자동화 및 효율성 향상 요구

### 1.3 범위
- FBX 본 구조 자동 분석
- Biped 자동 생성 및 크기 조정
- 애니메이션 데이터 베이킹
- 배치 처리 기능
- PyJalLib 기존 모듈과의 통합

---

## 2. 요구사항 분석

### 2.1 기능적 요구사항 (Functional Requirements)

#### 2.1.1 핵심 기능 (Core Features)
| 기능 ID | 기능명 | 설명 | 우선순위 |
|---------|--------|------|----------|
| F001 | FBX 본 구조 분석 | FBX 파일의 본 계층 구조를 분석하여 각 부위별 본 개수 파악 | High |
| F002 | Biped 자동 생성 | 분석된 본 구조를 바탕으로 적절한 Biped 생성 | High |
| F003 | 크기 자동 조정 | FBX 본 간 거리를 측정하여 Biped 크기 자동 조정 | High |
| F004 | 본 매핑 시스템 | FBX 본과 Biped 본 간의 매핑 테이블 관리 | High |
| F005 | 애니메이션 베이킹 | FBX 애니메이션 데이터를 Biped에 베이킹 | Medium |

#### 2.1.2 추가 기능 (Additional Features)
| 기능 ID | 기능명 | 설명 | 우선순위 |
|---------|--------|------|----------|
| F006 | 배치 처리 | 여러 FBX 파일 일괄 처리 | Medium |
| F007 | FIG 파일 지원 | 미리 정의된 Biped 구조 파일 지원 | Medium |
| F008 | 키프레임 최적화 | 불필요한 키프레임 제거 및 최적화 | Low |
| F009 | 네임스페이스 정리 | FBX 네임스페이스 자동 제거 | Low |
| F010 | 플립 수정 | 애니메이션 플립 현상 자동 수정 | Low |

### 2.2 비기능적 요구사항 (Non-Functional Requirements)

#### 2.2.1 성능 요구사항
- 단일 FBX 파일 처리 시간: 30초 이내
- 메모리 사용량: 1GB 이하 (일반적인 캐릭터 기준)
- 동시 처리 가능한 FBX 파일 수: 10개 이상

#### 2.2.2 호환성 요구사항
- 3DS Max 2020 이상 지원
- Python 3.7 이상 지원
- PyJalLib 기존 모듈과 100% 호환성

#### 2.2.3 사용성 요구사항
- 간단한 API 인터페이스 제공
- 명확한 에러 메시지 및 로깅
- 진행 상황 표시 기능

---

## 3. 기술적 사양

### 3.1 아키텍처 설계

#### 3.1.1 모듈 구조 (업데이트됨)
```
pyjallib/max/
├── mocap.py           # 메인 모듈 (완료: BipedBoneMapping, MocapRetargeter)
├── mocapAnalyzer.py   # FBX 분석 클래스 (예정)
├── bipedGenerator.py  # Biped 생성 클래스 (예정)
└── animationBaker.py  # 애니메이션 베이킹 클래스 (예정)
```

**현재 구현 상태**:
- ✅ `mocap.py`: BipedBoneMapping 클래스 (본 매핑 관리)
- ✅ 전체 Biped 본 구조 정의 (202개 매핑)
- ✅ JSON 저장/불러오기 기능
- ⏳ MocapRetargeter 클래스 (스켈레톤 구현)
- ⏳ FBX 분석 기능 (TODO)
- ⏳ Biped 생성 기능 (TODO)
- ⏳ 애니메이션 리타겟팅 (TODO)

#### 3.1.2 클래스 설계
```python
class MocapConverter:
    """메인 모캡 변환 클래스"""
    - fbx_to_biped()
    - batch_process()
    - validate_mapping()

class FbxAnalyzer:
    """FBX 구조 분석 클래스"""
    - analyze_bone_structure()
    - count_bones_by_type()
    - calculate_biped_height()

class BipedGenerator:
    """Biped 생성 및 조정 클래스"""
    - create_biped()
    - resize_biped()
    - map_bones()

class AnimationBaker:
    """애니메이션 베이킹 클래스"""
    - bake_animation()
    - optimize_keyframes()
```

### 3.2 데이터 구조

#### 3.2.1 본 매핑 구조 (완료)
```python
# BipedBoneMapping 클래스로 구현됨
mapping_data = {
    "metadata": {
        "UpAxis": "Z"
    },
    "biped_mapping": [
        {
            "bip": "Com",              # Biped 본 이름
            "fbx": "",                 # 사용자가 설정할 FBX 본 이름
            "biped_index": 13,         # Biped 계층 구조 인덱스
            "biped_link": 1            # 링크 번호
        },
        # ... 총 202개의 매핑 엔트리
    ]
}
```

#### 3.2.2 주요 클래스 구조 (완료)
```python
class BipedBoneMapping:
    """Biped 본 매핑 관리 클래스"""
    def save_mapping(self, file_path: str) -> bool
    def load_mapping(self, file_path: str) -> bool  
    def set_fbx_bone_name(self, bip_name: str, fbx_name: str) -> bool
    def get_fbx_bone_name(self, bip_name: str) -> Optional[str]
    def get_biped_info(self, bip_name: str) -> Optional[Dict]

class MocapRetargeter:
    """모션 캡처 리타겟팅 메인 클래스"""
    def analyze_fbx_structure(self, fbx_nodes: List[str]) -> Dict
    def create_biped(self, height: float = 170.0) -> bool
    def resize_biped(self) -> bool
    def retarget_animation(self, start_frame: int, end_frame: int) -> bool
```

#### 3.2.3 Biped 본 구조 (완료)
- **COM**: 1개 (Center of Mass)
- **Pelvis**: 1개
- **Spine**: 10개 (Spine, Spine1-Spine9)
- **Neck**: 25개 (Neck, Neck1-Neck24)
- **Head**: 1개
- **Arms**: 좌우 각 4개 (Clavicle, UpperArm, Forearm, Hand)
- **Fingers**: 좌우 각 15개 (5개 손가락 × 3개 링크)
- **Legs**: 좌우 각 4개 (Thigh, Calf, HorseLink, Foot)
- **Toes**: 좌우 각 15개 (5개 발가락 × 3개 링크)
- **Tail**: 25개 (Tail, Tail1-Tail24)
- **Ponytail**: 각 25개씩 2개 그룹
- **Props**: 3개 (Prop1, Prop2, Prop3)

**총 매핑 항목**: 202개

---

## 4. 구현 계획

### 4.1 개발 단계별 계획

#### Phase 1: 기반 구조 설계 (1주)
**목표**: 모듈 기본 구조 및 인터페이스 설계
**주요 작업**:
- [ ] PyJalLib 기존 구조 분석
- [ ] mocap.py 모듈 클래스 설계
- [ ] 기본 인터페이스 정의
- [ ] 의존성 관계 설정

**완료 기준**:
- 클래스 다이어그램 완성
- 기본 모듈 구조 생성
- 기존 모듈과의 통합성 검증

#### Phase 2: FBX 분석 기능 (1주)
**목표**: FBX 노드 구조 분석 및 본 카운팅 기능 구현
**주요 작업**:
- [ ] FbxAnalyzer 클래스 구현
- [ ] 본 구조 분석 알고리즘 구현
- [ ] 부위별 본 개수 카운팅
- [ ] 바이패드 높이 계산 로직

**완료 기준**:
- FBX 파일에서 본 구조 정확히 분석
- BIPPY와 동일한 카운팅 결과 도출
- 단위 테스트 통과

#### Phase 3: Biped 생성 및 설정 (1주)
**목표**: Biped 자동 생성 및 기본 설정 기능 구현
**주요 작업**:
- [x] BipedBoneMapping 클래스 구현 (완료)
- [x] 전체 Biped 본 구조 정의 (완료)  
- [x] 저장/불러오기 기능 구현 (완료)
- [ ] BipedGenerator 클래스 구현
- [ ] biped.createNew 기능 구현

**완료 기준**:
- FBX 분석 결과로 Biped 정확히 생성
- 본 매핑이 올바르게 설정
- 기본 크기 및 위치 설정 완료

#### Phase 4: 크기 조정 기능 (1.5주)
**목표**: Biped 크기를 FBX에 맞춰 자동 조정
**주요 작업**:
- [ ] Figure Mode 제어 구현
- [ ] 각 부위별 거리 측정 및 스케일 조정
- [ ] 위치/회전 최종 조정
- [ ] Clavicle 및 팔 본 처리

**완료 기준**:
- BIPPY와 동일한 크기 조정 결과
- 모든 부위가 정확히 조정됨
- Figure Mode 안정적 제어

#### Phase 5: 통합 및 헬퍼 기능 (1주)
**목표**: 주요 기능 통합 및 유틸리티 구현
**주요 작업**:
- [ ] MocapConverter 메인 클래스 구현
- [ ] fbx_to_biped() 통합 메서드
- [ ] 에러 처리 및 로깅
- [ ] 진행 상황 표시

**완료 기준**:
- 원클릭 FBX → Biped 변환 가능
- 안정적인 에러 처리
- 사용자 친화적 인터페이스

#### Phase 6: 테스트 및 문서화 (1주)
**목표**: 품질 보증 및 사용자 가이드 작성
**주요 작업**:
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 수행
- [ ] 사용 예제 및 문서 작성
- [ ] README 업데이트

**완료 기준**:
- 모든 테스트 통과
- 완전한 문서화
- 사용 예제 제공

#### Phase 7: 고급 기능 (2주, 선택사항)
**목표**: 추가 기능 및 최적화
**주요 작업**:
- [ ] 배치 처리 기능
- [ ] AnimationBaker 클래스 구현
- [ ] 키프레임 최적화
- [ ] Blade Tools 기능

**완료 기준**:
- 배치 처리 안정적 동작
- 애니메이션 베이킹 정확성
- 성능 최적화 완료

### 4.2 개발 일정
```
총 개발 기간: 6-8주
├── Phase 1: Week 1
├── Phase 2: Week 2  
├── Phase 3: Week 3
├── Phase 4: Week 4-5
├── Phase 5: Week 6
├── Phase 6: Week 7
└── Phase 7: Week 8 (선택)
```

---

## 5. 성공 지표

### 5.1 기술적 성공 지표
- [ ] BIPPY와 95% 이상 동일한 변환 결과
- [ ] 단일 FBX 처리 시간 30초 이내
- [ ] 메모리 사용량 1GB 이하
- [ ] 코드 커버리지 90% 이상

### 5.2 사용성 성공 지표
- [ ] 3줄 이하 코드로 기본 변환 가능
- [ ] 명확한 에러 메시지 제공
- [ ] 완전한 문서화 및 예제 제공

### 5.3 호환성 성공 지표
- [ ] PyJalLib 기존 모듈과 100% 호환
- [ ] 3DS Max 2020+ 지원
- [ ] Python 3.7+ 지원

---

## 6. 리스크 및 제약사항

### 6.1 기술적 리스크
| 리스크 | 확률 | 영향도 | 대응 방안 |
|--------|------|--------|-----------|
| pymxs API 제한 | Medium | High | 기존 PyJalLib 모듈 활용 |
| Biped API 복잡성 | High | Medium | BIPPY 코드 세밀 분석 |
| 성능 이슈 | Low | Medium | 단계적 최적화 |

### 6.2 일정 리스크
| 리스크 | 확률 | 영향도 | 대응 방안 |
|--------|------|--------|-----------|
| BIPPY 분석 지연 | Low | High | 충분한 분석 시간 확보 |
| 테스트 데이터 부족 | Medium | Medium | 다양한 FBX 샘플 수집 |
| 통합 이슈 | Medium | High | 단계별 통합 테스트 |

### 6.3 제약사항
- 3DS Max 환경에서만 동작
- pymxs 모듈 의존성
- BIPPY 기능 범위 내에서 구현

---

## 7. 품질 보증

### 7.1 테스트 전략
- **단위 테스트**: 각 클래스 및 메서드별 테스트
- **통합 테스트**: 모듈 간 연동 테스트
- **성능 테스트**: 다양한 크기의 FBX 파일 테스트
- **호환성 테스트**: 다양한 3DS Max 버전 테스트

### 7.2 코드 품질 기준
- PEP 8 스타일 가이드 준수
- Type Hints 사용
- Docstring 완전 작성
- 코드 리뷰 필수

---

## 8. 결론 및 다음 단계

### 8.1 기대 효과
- 모션 캡처 워크플로우 자동화
- PyJalLib 생태계 확장
- 사용자 생산성 향상

### 8.2 다음 단계
1. **승인 및 자원 할당**: 개발 팀 및 일정 확정
2. **Phase 1 시작**: 기반 구조 설계 착수
3. **정기 리뷰**: 주간 진행 상황 점검
4. **베타 테스트**: Phase 6 완료 후 사용자 테스트

---

**승인자**: _______________  
**승인일**: _______________ 