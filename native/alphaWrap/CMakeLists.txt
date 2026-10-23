# pyjallib.native.alpha_wrap_native 빌드 정의 - native/build_native.py가 부른다.
#
# 벤더링 사본(src/, predicates/)만 쓴다 - FetchContent 없음(빌드가 네트워크를 타지 않는다, VENDORED.md).
# MSVC 정적 런타임(/MT): .pyd가 python310.dll·KERNEL32.dll 외에 의존하지 않게 한다. 3ds Max가 먼저 로드한 msvcp140.dll과
# 빌드 툴셋의 버전이 어긋나는 문제를 피한다(PRD §8.1 - /MD 변형은 MSVCP140·VCRUNTIME140에 의존했다).
cmake_minimum_required(VERSION 3.18)
project(alpha_wrap_native LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded")

set(AW_UPSTREAM_COMMIT "00564179c0c839db85514db97caaa6890944542a" CACHE STRING "벤더링한 alpha-wrap 커밋")
set(AW_PREDICATES_COMMIT "49c33980c55e9576c558a30a066940c2e360fcc2" CACHE STRING "벤더링한 predicates 커밋")

add_library(aw_predicates STATIC predicates/src/predicates.c predicates/src/constants.c)
target_include_directories(aw_predicates PUBLIC predicates/include)
set_target_properties(aw_predicates PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(awcore STATIC src/predicates.cpp src/aabb_tree.cpp src/delaunay.cpp src/alpha_wrap.cpp)
target_include_directories(awcore PUBLIC src)
target_link_libraries(awcore PUBLIC aw_predicates)
set_target_properties(awcore PROPERTIES POSITION_INDEPENDENT_CODE ON)

find_package(Python 3.10 EXACT REQUIRED COMPONENTS Interpreter Development.Module)
find_package(nanobind CONFIG REQUIRED)
nanobind_add_module(alpha_wrap_native NB_STATIC pyjallib_bindings.cpp)
target_link_libraries(alpha_wrap_native PRIVATE awcore)
target_compile_definitions(alpha_wrap_native PRIVATE
  AW_UPSTREAM_COMMIT="${AW_UPSTREAM_COMMIT}"
  AW_PREDICATES_COMMIT="${AW_PREDICATES_COMMIT}"
  AW_RUNTIME="MT")
