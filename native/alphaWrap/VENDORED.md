# alphaWrap - 벤더링 기록

Alpha Wrapping with an Offset(Portaneri et al., ACM TOG 2022)의 CGAL 없는 C++ 구현을 `pyjallib.native.alpha_wrap_native`로 빌드하기 위해
**고정 커밋 사본**으로 들여왔다. 업스트림 추종은 의도적으로만 한다(8커밋짜리 젊은 저장소 - 변경을 회귀 비교 없이 받지 않는다).

## 출처

| 구성 | 저장소 | 커밋 | 라이선스 |
|:---|:---|:---|:---|
| 코어 (`src/`) | https://github.com/alecjacobson/alpha-wrap | `00564179c0c839db85514db97caaa6890944542a` (2026-08-31, "README: fix paper author attribution") | MIT - `LICENSE` (원문 사본) |
| 술어 (`predicates/`) | https://github.com/danshapero/predicates | `49c33980c55e9576c558a30a066940c2e360fcc2` (2024-06-23, "silence CMake warnings") | LICENSE 파일 없음. `predicates/README.md`: Shewchuk 원본 코드는 "Placed in the public domain", 포크 저자는 라이선스를 부여할 수 없다고 명시 |

업스트림 `cmake/dependencies.cmake`는 술어를 `FetchContent` `GIT_TAG master`로 **빌드 때마다 내려받는다**(고정 안 됨). 이 사본은 그 커밋을
들여와 빌드가 네트워크를 타지 않게 한다.

## 가져온 파일

- 코어: `src/geom.hpp`, `src/predicates.hpp`, `src/predicates.cpp`, `src/aabb_tree.hpp`, `src/aabb_tree.cpp`, `src/delaunay.hpp`,
  `src/delaunay.cpp`, `src/alpha_wrap.hpp`, `src/alpha_wrap.cpp` + `LICENSE`
- 술어: `predicates/include/predicates.h`, `predicates/include/predicatesDLLExport.h`, `predicates/src/predicates.c`,
  `predicates/src/constants.c`, `predicates/src/constants.h` + `predicates/README.md`(라이선스 진술 근거)
- 가져오지 않은 것: 업스트림 `python/`(numpy 바인딩 - 자체 바인딩 `pyjallib_bindings.cpp`로 대체), `src/main.cpp`·`src/mesh_io.hpp`(CLI),
  `tests/`·`tools/`·`benchmarks/`, CGAL 백엔드

## 수정

**없다.** 파일은 위 커밋과 내용이 같다(작업본 개행은 git 설정을 따른다). 빌드 경고 C4273(술어 헤더가 `predicates_EXPORTS` 미정의 시
`dllimport`로 선언하는데 정적 라이브러리로 빌드함)은 링크·동작에 무해해 소스를 고치지 않는다.

## 검증 (2026-10-23, PyJalLib Phase 0 - `.ai_planning/.../active_prd.md` §8.1)

- 업스트림 그대로 CMake + MSVC 14.44 Release 빌드, `ctest` 1/1 통과.
- 이 사본 + 자체 바인딩을 네트워크 없이 빌드 -> 콘솔 CPython 3.10.14와 3ds Max 2024에서 로드, 정육면체·구 감싸기 닫힘·부호 부피 > 0, 결과 동일.

## 갱신 절차

1. 새 커밋을 스크래치에 받아 위 파일만 덮는다(목록 밖 파일이 생겼으면 의존을 확인한다).
2. `python native/build_native.py`로 다시 빌드한다.
3. PyJalLib Type A(`tests/test_native_alpha_wrap.py`·`tests/test_clip_mesh.py`)와, 실기 슬롯 회귀(같은 입력의 W 삼각형 수·닫힘·과다)를 비교한다.
4. 이 문서의 커밋 해시와 `CMakeLists.txt`의 `AW_UPSTREAM_COMMIT`/`AW_PREDICATES_COMMIT`를 함께 바꾼다.
