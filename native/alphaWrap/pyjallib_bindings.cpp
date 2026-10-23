// pyjallib.native.alpha_wrap_native - Alpha Wrap 코어의 numpy 없는 nanobind 바인딩.
//
// 왜 업스트림 python/bindings.cpp를 쓰지 않는가: 업스트림은 numpy 배열을 받고 돌려준다. pyjallib은 numpy에 의존하지 않고
// (DCC 내장 Python에 추가 패키지를 설치할 수 없다), 순수 모듈(clipMesh)이 리스트로 일하므로 평탄한 시퀀스로 주고받는다.
// 입력을 C++ 버퍼로 옮긴 뒤 wrap 동안 GIL을 푼다 - 여러 스레드에서 동시에 불러도 서로 막지 않는다.
#include <cstdint>
#include <stdexcept>
#include <vector>

#include <nanobind/nanobind.h>
#include <nanobind/stl/tuple.h>
#include <nanobind/stl/vector.h>

#include "alpha_wrap.hpp"

namespace nb = nanobind;
using namespace nb::literals;

#ifndef AW_UPSTREAM_COMMIT
#define AW_UPSTREAM_COMMIT "unknown"
#endif
#ifndef AW_PREDICATES_COMMIT
#define AW_PREDICATES_COMMIT "unknown"
#endif
#ifndef AW_RUNTIME
#define AW_RUNTIME "unknown"
#endif

namespace {

// 평탄한 버텍스 좌표(x0, y0, z0, x1, ...)와 삼각형 인덱스(a0, b0, c0, ...)를 감싼다.
// 잘못된 인자는 감싸기 전에 거부한다(업스트림은 범위 밖 면을 조용히 건너뛴다 - 여기서는 호출자 결함으로 본다).
nb::tuple wrap_flat(const std::vector<double>& verts, const std::vector<int64_t>& tris, double alpha, double offset,
                    bool manifold) {
  if (verts.size() % 3 != 0) throw std::invalid_argument("verts length must be a multiple of 3");
  if (tris.size() % 3 != 0) throw std::invalid_argument("tris length must be a multiple of 3");
  if (tris.empty()) throw std::invalid_argument("tris must not be empty");
  if (!(alpha > 0)) throw std::invalid_argument("alpha must be > 0");
  if (!(offset > 0)) throw std::invalid_argument("offset must be > 0");
  const int64_t n = static_cast<int64_t>(verts.size() / 3);
  std::vector<aw::Triangle> soup;
  soup.reserve(tris.size() / 3);
  for (size_t i = 0; i < tris.size(); i += 3) {
    aw::Triangle t;
    for (int k = 0; k < 3; ++k) {
      const int64_t vi = tris[i + k];
      if (vi < 0 || vi >= n) throw std::out_of_range("triangle index out of range");
      t[k] = aw::Vec3{verts[3 * vi], verts[3 * vi + 1], verts[3 * vi + 2]};
    }
    soup.push_back(t);
  }
  aw::WrapStats st;
  aw::Mesh mesh;
  {
    nb::gil_scoped_release release;
    mesh = aw::alpha_wrap(soup, alpha, offset, manifold, &st);
  }
  std::vector<double> outV;
  outV.reserve(mesh.V.size() * 3);
  for (const auto& p : mesh.V) {
    outV.push_back(p.x);
    outV.push_back(p.y);
    outV.push_back(p.z);
  }
  std::vector<int64_t> outF;
  outF.reserve(mesh.F.size() * 3);
  for (const auto& f : mesh.F) {
    outF.push_back(f[0]);
    outF.push_back(f[1]);
    outF.push_back(f[2]);
  }
  nb::dict stats;
  stats["steiner_points"] = st.steiner_points;
  stats["rule1"] = st.rule1;
  stats["rule2"] = st.rule2;
  stats["carved"] = st.carved;
  stats["gates_popped"] = st.gates_popped;
  stats["manifold_cells_reclaimed"] = st.manifold_cells_reclaimed;
  stats["output_vertices"] = st.output_vertices;
  stats["output_faces"] = st.output_faces;
  return nb::make_tuple(outV, outF, stats);
}

}  // namespace

NB_MODULE(alpha_wrap_native, m) {
  m.doc() = "Alpha Wrapping with an Offset (CGAL-free, alecjacobson/alpha-wrap) - pyjallib flat-list binding";
  m.def("wrap", &wrap_flat, "verts"_a, "tris"_a, "alpha"_a, "offset"_a, "manifold"_a = true,
        "Wrap a triangle soup given as flat lists. Returns (verts_flat, tris_flat, stats). "
        "alpha/offset are absolute (> 0). Releases the GIL while wrapping.");
  m.attr("UPSTREAM_COMMIT") = AW_UPSTREAM_COMMIT;
  m.attr("PREDICATES_COMMIT") = AW_PREDICATES_COMMIT;
  m.attr("RUNTIME") = AW_RUNTIME;
}
