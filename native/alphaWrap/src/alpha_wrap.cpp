#include "alpha_wrap.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <queue>
#include <unordered_map>

#include "predicates.hpp"

namespace aw {

namespace {

constexpr double kInf = std::numeric_limits<double>::infinity();

double tri_squared_circumradius(const Vec3& a, const Vec3& b, const Vec3& c) {
  Vec3 ab = b - a, ac = c - a;
  Vec3 n = cross(ab, ac);
  double n2 = norm2(n);
  if (n2 <= 0) return kInf;  // degenerate triangle
  return norm2(ab) * norm2(c - b) * norm2(ac) / (4.0 * n2);
}

struct Gate {
  double r2;
  Cid outside;
  int fi;
  std::array<Vid, 3> fv;  // sorted facet-vertex snapshot for staleness check
};
struct GateLess {
  bool operator()(const Gate& a, const Gate& b) const { return a.r2 < b.r2; }
};

std::array<Vid, 3> sorted_facet(const Delaunay& dt, Cid c, int fi) {
  const Cell& cc = dt.cell(c);
  std::array<Vid, 3> f = {cc.v[Delaunay::FACET[fi][0]], cc.v[Delaunay::FACET[fi][1]],
                          cc.v[Delaunay::FACET[fi][2]]};
  std::sort(f.begin(), f.end());
  return f;
}

}  // namespace

void AlphaWrap::ensure_label_capacity() {
  if (static_cast<int>(label_.size()) < dt_.num_cells())
    label_.resize(dt_.num_cells(), OUTSIDE);
}

bool AlphaWrap::facet_touches_scaffold(Cid c, int fi) const {
  const Cell& cc = dt_.cell(c);
  for (int k = 0; k < 3; ++k)
    if (cc.v[Delaunay::FACET[fi][k]] < first_real_vertex_) return true;
  return false;
}

Vec3 AlphaWrap::facet_outward_normal(Cid c, int fi) const {
  const Cell& cc = dt_.cell(c);
  const Vec3& a = dt_.point(cc.v[Delaunay::FACET[fi][0]]);
  const Vec3& b = dt_.point(cc.v[Delaunay::FACET[fi][1]]);
  const Vec3& d = dt_.point(cc.v[Delaunay::FACET[fi][2]]);
  Vec3 n = cross(b - a, d - a);  // points away from cc.v[fi] (outward from c)
  double len = norm(n);
  return len > 0 ? n / len : n;
}

double AlphaWrap::gate_squared_radius(Cid outside, int fi, Cid inside) const {
  if (dt_.cell_is_outer(outside) || dt_.cell_is_outer(inside) ||
      facet_touches_scaffold(outside, fi))
    return kInf;  // permissive
  const Cell& oc = dt_.cell(outside);
  const Vec3& p1 = dt_.point(oc.v[Delaunay::FACET[fi][0]]);
  const Vec3& p2 = dt_.point(oc.v[Delaunay::FACET[fi][1]]);
  const Vec3& p3 = dt_.point(oc.v[Delaunay::FACET[fi][2]]);
  Vec3 cc_out = dt_.circumcenter(outside);
  Vec3 cc_in = dt_.circumcenter(inside);
  Sign s1 = orient3d(p1, p2, p3, cc_out);
  Sign s2 = orient3d(p1, p2, p3, cc_in);
  if (s1 != s2) {
    // Dual Voronoi edge crosses the facet: min empty-sphere radius is the
    // facet's own circumradius.
    return tri_squared_circumradius(p1, p2, p3);
  }
  return std::min(dt_.squared_circumradius(outside),
                  dt_.squared_circumradius(inside));
}

bool AlphaWrap::gate_traversable(Cid outside, int fi, Cid inside) const {
  return gate_squared_radius(outside, fi, inside) > alpha2_;
}

bool AlphaWrap::compute_steiner_point(Cid outside, int fi, Cid inside, Vec3& out,
                                      int& rule) const {
  Vec3 cc_in = dt_.circumcenter(inside);
  Vec3 cc_out;
  if (dt_.cell_is_outer(outside)) {
    // Outer cell models an infinite cell: the dual Voronoi edge is a ray from
    // cc_in outward through the facet. Use a far point along that ray.
    int back = -1;
    const Cell& ic = dt_.cell(inside);
    for (int k = 0; k < 4; ++k)
      if (ic.nbr[k] == outside) { back = k; break; }
    Vec3 n = back >= 0 ? facet_outward_normal(inside, back)
                       : facet_outward_normal(outside, fi) * -1.0;
    double L = 3.0 * oracle_.bbox().diagonal() + 1.0;
    cc_out = cc_in + n * L;
  } else {
    cc_out = dt_.circumcenter(outside);
  }

  // Rule 1: dual edge crosses the offset iso-surface.
  Vec3 s;
  if (oracle_.first_offset_crossing(cc_out, cc_in, prm_.offset, s)) {
    out = s;
    rule = 1;
    return true;
  }
  // Rule 2: inside cell still overlaps the input.
  const Cell& ic = dt_.cell(inside);
  const Vec3& a = dt_.point(ic.v[0]);
  const Vec3& b = dt_.point(ic.v[1]);
  const Vec3& c = dt_.point(ic.v[2]);
  const Vec3& d = dt_.point(ic.v[3]);
  if (oracle_.do_intersect_tet(a, b, c, d)) {
    Vec3 p = oracle_.closest_point(cc_in);
    Vec3 dir = cc_in - p;
    double len = norm(dir);
    if (len > 0)
      out = p + dir * (prm_.offset / len);
    else
      out = p + Vec3{prm_.offset, 0, 0};
    rule = 2;
    return true;
  }
  return false;
}

Mesh AlphaWrap::operator()(const std::vector<Triangle>& soup,
                           const WrapParams& prm) {
  prm_ = prm;
  stats_ = WrapStats{};
  alpha2_ = prm.alpha * prm.alpha;
  oracle_.build(soup);

  // ---- loose bounding box: scale 1.2 about center, expand by sqrt(3)*offset ----
  Box ib = oracle_.bbox();
  Vec3 center = ib.center();
  Vec3 half = ib.extent() * (0.5 * 1.2);
  double ext = std::sqrt(3.0) * prm.offset;
  Box loose;
  loose.lo = center - half - Vec3{ext, ext, ext};
  loose.hi = center + half + Vec3{ext, ext, ext};

  dt_.init(loose);
  // Insert 8 loose-bbox corners (scaffolding). ids 4..11 (super verts are 0..3).
  for (int i = 0; i < 8; ++i) {
    Vec3 corner{(i & 1) ? loose.hi.x : loose.lo.x,
                (i & 2) ? loose.hi.y : loose.lo.y,
                (i & 4) ? loose.hi.z : loose.lo.z};
    dt_.insert(corner);
  }
  first_real_vertex_ = dt_.num_vertices();  // = 12

  // ---- label all cells: outer -> OUTSIDE, finite -> INSIDE ----
  label_.assign(dt_.num_cells(), OUTSIDE);
  for (Cid c = 0; c < dt_.num_cells(); ++c) {
    if (!dt_.cell_alive(c)) continue;
    set_label(c, dt_.cell_is_outer(c) ? OUTSIDE : INSIDE);
  }

  std::priority_queue<Gate, std::vector<Gate>, GateLess> pq;
  auto enqueue = [&](Cid oc, int fi) {
    Cid inside = dt_.cell(oc).nbr[fi];
    if (inside == NO_CELL || !dt_.cell_alive(inside)) return;
    if (label_of(oc) != OUTSIDE || label_of(inside) != INSIDE) return;
    double r2 = gate_squared_radius(oc, fi, inside);
    if (r2 <= alpha2_) return;  // not traversable
    pq.push(Gate{r2, oc, fi, sorted_facet(dt_, oc, fi)});
  };

  // Seed with all traversable outside/inside gates.
  for (Cid c = 0; c < dt_.num_cells(); ++c) {
    if (!dt_.cell_alive(c) || label_of(c) != OUTSIDE) continue;
    for (int fi = 0; fi < 4; ++fi) enqueue(c, fi);
  }

  const long max_steiner = 5'000'000;
  std::vector<Cid> new_cells;

  while (!pq.empty()) {
    Gate g = pq.top();
    pq.pop();
    ++stats_.gates_popped;

    // Validate against staleness (cell recycling / relabeling).
    if (!dt_.cell_alive(g.outside) || label_of(g.outside) != OUTSIDE) continue;
    Cid inside = dt_.cell(g.outside).nbr[g.fi];
    if (inside == NO_CELL || !dt_.cell_alive(inside) ||
        label_of(inside) != INSIDE)
      continue;
    if (sorted_facet(dt_, g.outside, g.fi) != g.fv) continue;

    Vec3 sp;
    int rule = 0;
    if (compute_steiner_point(g.outside, g.fi, inside, sp, rule)) {
      if (stats_.steiner_points >= max_steiner) break;
      dt_.insert(sp, &new_cells);
      ++stats_.steiner_points;
      if (rule == 1) ++stats_.rule1; else ++stats_.rule2;
      ensure_label_capacity();
      for (Cid nc : new_cells)
        set_label(nc, dt_.cell_is_outer(nc) ? OUTSIDE : INSIDE);
      // Enqueue every new outside/inside boundary gate.
      for (Cid nc : new_cells) {
        for (int fi = 0; fi < 4; ++fi) {
          Cid m = dt_.cell(nc).nbr[fi];
          if (m == NO_CELL || !dt_.cell_alive(m)) continue;
          if (label_of(nc) == OUTSIDE && label_of(m) == INSIDE) enqueue(nc, fi);
          else if (label_of(nc) == INSIDE && label_of(m) == OUTSIDE) {
            int back = -1;
            for (int k = 0; k < 4; ++k)
              if (dt_.cell(m).nbr[k] == nc) { back = k; break; }
            if (back >= 0) enqueue(m, back);
          }
        }
      }
    } else {
      // Carve: flip the inside cell to OUTSIDE and open its other 3 facets.
      set_label(inside, OUTSIDE);
      ++stats_.carved;
      for (int fi = 0; fi < 4; ++fi) {
        Cid m = dt_.cell(inside).nbr[fi];
        if (m == NO_CELL || !dt_.cell_alive(m)) continue;
        if (label_of(m) == INSIDE) enqueue(inside, fi);
      }
    }
  }

  if (prm_.manifold) make_manifold();
  Mesh mesh = extract();
  stats_.output_vertices = static_cast<int>(mesh.V.size());
  stats_.output_faces = static_cast<int>(mesh.F.size());
  return mesh;
}

namespace {
// Union-find over a small local set (indices into a vector).
struct DSU {
  std::vector<int> p;
  void reset(int n) { p.resize(n); for (int i = 0; i < n; ++i) p[i] = i; }
  int find(int x) { while (p[x] != x) { p[x] = p[p[x]]; x = p[x]; } return x; }
  void uni(int a, int b) { p[find(a)] = find(b); }
};
}  // namespace

void AlphaWrap::make_manifold() {
  // Build vertex -> incident live cells (labels change during the pass, but the
  // incidence relation does not, since no points are inserted here).
  std::unordered_map<Vid, std::vector<Cid>> incident;
  for (Cid c = 0; c < dt_.num_cells(); ++c) {
    if (!dt_.cell_alive(c)) continue;
    const Cell& cc = dt_.cell(c);
    for (int k = 0; k < 4; ++k) incident[cc.v[k]].push_back(c);
  }

  // Count connected components, among v's incident cells, of those satisfying
  // `want_solid`, where two incident cells connect if their shared facet
  // contains v. Returns component count (0 if none).
  auto components = [&](Vid v, bool want_solid) -> int {
    const auto& cells = incident[v];
    int n = static_cast<int>(cells.size());
    std::unordered_map<Cid, int> idx;
    std::vector<int> members;
    for (int i = 0; i < n; ++i)
      if (is_solid(cells[i]) == want_solid) { idx[cells[i]] = static_cast<int>(members.size()); members.push_back(cells[i]); }
    int m = static_cast<int>(members.size());
    if (m == 0) return 0;
    DSU dsu; dsu.reset(m);
    for (int i = 0; i < m; ++i) {
      Cid c = members[i];
      const Cell& cc = dt_.cell(c);
      for (int fi = 0; fi < 4; ++fi) {
        // facet fi contains v?
        bool has_v = false;
        for (int t = 0; t < 3; ++t) if (cc.v[Delaunay::FACET[fi][t]] == v) has_v = true;
        if (!has_v) continue;
        Cid o = cc.nbr[fi];
        if (o == NO_CELL) continue;
        auto it = idx.find(o);
        if (it != idx.end()) dsu.uni(i, it->second);
      }
    }
    int comps = 0;
    for (int i = 0; i < m; ++i) if (dsu.find(i) == i) ++comps;
    return comps;
  };

  auto is_boundary_vertex = [&](Vid v) {
    bool solid = false, out = false;
    for (Cid c : incident[v]) { if (is_solid(c)) solid = true; else out = true; }
    return solid && out;
  };
  auto nonmanifold = [&](Vid v) {
    if (!is_boundary_vertex(v)) return false;
    // A manifold boundary vertex has a single solid umbrella and a single
    // outside umbrella.
    return components(v, true) > 1 || components(v, false) > 1;
  };

  double longest_edge2 = 0;  // (reused per cell)
  auto cell_longest_edge2 = [&](Cid c) {
    const Cell& cc = dt_.cell(c);
    double mx = 0;
    for (int i = 0; i < 4; ++i)
      for (int j = i + 1; j < 4; ++j)
        mx = std::max(mx, dist2(dt_.point(cc.v[i]), dt_.point(cc.v[j])));
    return mx;
  };
  (void)longest_edge2;

  std::vector<Vid> stack;
  for (auto& [v, cells] : incident)
    if (v >= first_real_vertex_ && nonmanifold(v)) stack.push_back(v);

  long guard = 0;
  const long guard_max = 20'000'000;
  while (!stack.empty()) {
    if (++guard > guard_max) break;
    Vid v = stack.back();
    stack.pop_back();
    if (!nonmanifold(v)) continue;

    // Candidate finite OUTSIDE cells incident to v, preference-ordered.
    std::vector<Cid> cand;
    for (Cid c : incident[v])
      if (!is_solid(c) && !dt_.cell_is_outer(c)) cand.push_back(c);
    if (cand.empty()) continue;  // only exterior outside cells; cannot fix here
    auto has_scaffold = [&](Cid c) {
      const Cell& cc = dt_.cell(c);
      for (int k = 0; k < 4; ++k) if (cc.v[k] < first_real_vertex_) return true;
      return false;
    };
    std::stable_sort(cand.begin(), cand.end(), [&](Cid a, Cid b) {
      bool sa = has_scaffold(a), sb = has_scaffold(b);
      if (sa != sb) return !sa;  // prefer cells without scaffold vertices
      return cell_longest_edge2(a) < cell_longest_edge2(b);  // avoid spikes
    });

    for (Cid c : cand) {
      if (!nonmanifold(v)) break;
      set_label(c, MANIFOLD);
      ++stats_.manifold_cells_reclaimed;
      // Reclaiming c changes the boundary around its vertices; revisit them.
      const Cell& cc = dt_.cell(c);
      for (int k = 0; k < 4; ++k)
        if (cc.v[k] >= first_real_vertex_ && nonmanifold(cc.v[k]))
          stack.push_back(cc.v[k]);
    }
  }
}

Mesh AlphaWrap::extract() const {
  Mesh mesh;
  std::unordered_map<Vid, int> remap;
  auto vid_out = [&](Vid v) -> int {
    auto it = remap.find(v);
    if (it != remap.end()) return it->second;
    int id = static_cast<int>(mesh.V.size());
    remap.emplace(v, id);
    mesh.V.push_back(dt_.point(v));
    return id;
  };

  for (Cid c = 0; c < dt_.num_cells(); ++c) {
    if (!dt_.cell_alive(c)) continue;
    if (label_of(c) == OUTSIDE) continue;  // only solid cells emit
    const Cell& cc = dt_.cell(c);
    for (int fi = 0; fi < 4; ++fi) {
      Cid o = cc.nbr[fi];
      bool outside = (o == NO_CELL) || (label_of(o) == OUTSIDE);
      if (!outside) continue;
      // FACET triple normal points toward o (outward from the solid).
      Vid a = cc.v[Delaunay::FACET[fi][0]];
      Vid b = cc.v[Delaunay::FACET[fi][1]];
      Vid d = cc.v[Delaunay::FACET[fi][2]];
      mesh.F.push_back({vid_out(a), vid_out(b), vid_out(d)});
    }
  }
  return mesh;
}

Mesh alpha_wrap(const std::vector<Triangle>& soup, double alpha, double offset,
                bool manifold, WrapStats* stats) {
  AlphaWrap aw;
  WrapParams prm;
  prm.alpha = alpha;
  prm.offset = offset;
  prm.manifold = manifold;
  Mesh m = aw(soup, prm);
  if (stats) *stats = aw.stats();
  return m;
}

}  // namespace aw
