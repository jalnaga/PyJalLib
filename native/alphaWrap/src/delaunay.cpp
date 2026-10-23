#include "delaunay.hpp"

#include <algorithm>
#include <cassert>
#include <cstdio>
#include <unordered_map>
#include <utility>

#include "predicates.hpp"

namespace aw {

namespace {
inline uint64_t edge_key(Vid a, Vid b) {
  uint32_t lo = static_cast<uint32_t>(a < b ? a : b);
  uint32_t hi = static_cast<uint32_t>(a < b ? b : a);
  return (static_cast<uint64_t>(hi) << 32) | lo;
}
}  // namespace

void Delaunay::init(const Box& domain, double margin) {
  points_.clear();
  cells_.clear();
  free_cells_.clear();
  mark_.clear();
  mark_ctr_ = 0;
  live_cell_count_ = 0;
  last_cell_ = NO_CELL;

  Vec3 c = domain.empty() ? Vec3{0, 0, 0} : domain.center();
  double diag = domain.empty() ? 1.0 : domain.diagonal();
  if (diag <= 0) diag = 1.0;
  double s = margin * diag;

  // Regular tetrahedron directions (even-parity cube corners).
  const Vec3 dirs[4] = {{1, 1, 1}, {1, -1, -1}, {-1, 1, -1}, {-1, -1, 1}};
  for (int i = 0; i < 4; ++i) points_.push_back(c + dirs[i] * s);

  // Ensure the initial cell (0,1,2,3) is positively oriented; swap if not.
  std::array<Vid, 4> v{0, 1, 2, 3};
  if (orient3d(points_[0], points_[1], points_[2], points_[3]) !=
      Sign::POSITIVE) {
    std::swap(v[0], v[1]);
  }
  Cid c0 = new_cell();
  cells_[c0].v = v;
  cells_[c0].nbr = {NO_CELL, NO_CELL, NO_CELL, NO_CELL};
  last_cell_ = c0;
}

Cid Delaunay::new_cell() {
  Cid id;
  if (!free_cells_.empty()) {
    id = free_cells_.back();
    free_cells_.pop_back();
  } else {
    id = static_cast<Cid>(cells_.size());
    cells_.emplace_back();
  }
  cells_[id].alive = true;
  cells_[id].nbr = {NO_CELL, NO_CELL, NO_CELL, NO_CELL};
  ++live_cell_count_;
  return id;
}

void Delaunay::kill_cell(Cid c) {
  cells_[c].alive = false;
  free_cells_.push_back(c);
  --live_cell_count_;
}

int Delaunay::facet_index_of_neighbor(Cid c, Cid neighbor) const {
  const auto& cc = cells_[c];
  for (int i = 0; i < 4; ++i)
    if (cc.nbr[i] == neighbor) return i;
  return -1;
}

bool Delaunay::in_conflict(Cid c, const Vec3& p) const {
  const auto& cc = cells_[c];
  // Strictly inside the circumsphere. Cospherical (ZERO) treated as not-in-
  // conflict for now (general-position path; SoS layered separately).
  return insphere(points_[cc.v[0]], points_[cc.v[1]], points_[cc.v[2]],
                  points_[cc.v[3]], p) == Sign::POSITIVE;
}

Cid Delaunay::locate(const Vec3& p, Cid hint) const {
  Cid c = hint;
  if (c == NO_CELL || !cells_[c].alive) c = last_cell_;
  if (c == NO_CELL || !cells_[c].alive) {
    for (Cid i = 0; i < static_cast<Cid>(cells_.size()); ++i)
      if (cells_[i].alive) { c = i; break; }
  }
  const int max_steps = 2 * static_cast<int>(cells_.size()) + 16;
  Cid prev = NO_CELL;
  for (int step = 0; step < max_steps; ++step) {
    const auto& cc = cells_[c];
    Cid next = NO_CELL;
    for (int i = 0; i < 4; ++i) {
      if (cc.nbr[i] == prev) continue;  // don't walk straight back
      const Vec3& a = points_[cc.v[FACET[i][0]]];
      const Vec3& b = points_[cc.v[FACET[i][1]]];
      const Vec3& d = points_[cc.v[FACET[i][2]]];
      // Outward triple (a,b,d): p is beyond facet i iff on its positive side.
      if (orient3d(a, b, d, p) == Sign::POSITIVE) {
        if (cc.nbr[i] == NO_CELL) continue;  // p outside domain across a hull face
        next = cc.nbr[i];
        break;
      }
    }
    if (next == NO_CELL) {
      last_cell_ = c;
      return c;  // p is inside (closure of) c
    }
    prev = c;
    c = next;
  }
  last_cell_ = c;
  return c;  // fallback (shouldn't happen for valid input)
}

Vid Delaunay::insert(const Vec3& p, std::vector<Cid>* out_new_cells) {
  if (out_new_cells) out_new_cells->clear();
  Cid c0 = locate(p, last_cell_);
  // Duplicate detection against the located cell's vertices.
  for (int i = 0; i < 4; ++i) {
    Vid vi = cells_[c0].v[i];
    const Vec3& q = points_[vi];
    if (q.x == p.x && q.y == p.y && q.z == p.z) return vi;
  }

  Vid vp = static_cast<Vid>(points_.size());
  points_.push_back(p);

  // ---- gather conflict zone (BFS from c0) using stamps ----
  if (mark_.size() < cells_.size()) mark_.resize(cells_.size() + 1, 0);
  const uint32_t stamp_checked = ++mark_ctr_;
  const uint32_t stamp_conflict = ++mark_ctr_;

  std::vector<Cid> conflict;
  std::vector<Cid> stack;
  mark_[c0] = stamp_conflict;
  conflict.push_back(c0);
  stack.push_back(c0);
  while (!stack.empty()) {
    Cid c = stack.back();
    stack.pop_back();
    for (int i = 0; i < 4; ++i) {
      Cid o = cells_[c].nbr[i];
      if (o == NO_CELL) continue;
      if (mark_[o] == stamp_conflict || mark_[o] == stamp_checked) continue;
      if (in_conflict(o, p)) {
        mark_[o] = stamp_conflict;
        conflict.push_back(o);
        stack.push_back(o);
      } else {
        mark_[o] = stamp_checked;
      }
    }
  }

  // ---- stellate: create new cells from boundary facets to vp ----
  std::unordered_map<uint64_t, std::pair<Cid, int>> edge_map;
  edge_map.reserve(conflict.size() * 3);
  std::vector<Cid> new_cells;
  new_cells.reserve(conflict.size() * 2);

  for (Cid c : conflict) {
    for (int fi = 0; fi < 4; ++fi) {
      Cid o = cells_[c].nbr[fi];
      bool boundary = (o == NO_CELL) || (mark_[o] != stamp_conflict);
      if (!boundary) continue;
      Vid t0 = cells_[c].v[FACET[fi][0]];
      Vid t1 = cells_[c].v[FACET[fi][1]];
      Vid t2 = cells_[c].v[FACET[fi][2]];
      // New cell (t0,t2,t1,vp) is positively oriented (see delaunay.hpp).
      Cid w = new_cell();
      new_cells.push_back(w);
      cells_[w].v = {t0, t2, t1, vp};
      cells_[w].nbr[3] = o;
      if (o != NO_CELL) {
        int back = facet_index_of_neighbor(o, c);
        cells_[o].nbr[back] = w;
      }
      // facet 0 opp t0 -> edge {t1,t2}; facet 1 opp t2 -> {t0,t1};
      // facet 2 opp t1 -> {t0,t2}.
      const uint64_t ek[3] = {edge_key(t1, t2), edge_key(t0, t1),
                              edge_key(t0, t2)};
      for (int lf = 0; lf < 3; ++lf) {
        auto it = edge_map.find(ek[lf]);
        if (it == edge_map.end()) {
          edge_map.emplace(ek[lf], std::make_pair(w, lf));
        } else {
          Cid w2 = it->second.first;
          int lf2 = it->second.second;
          cells_[w].nbr[lf] = w2;
          cells_[w2].nbr[lf2] = w;
        }
      }
    }
  }

  for (Cid c : conflict) kill_cell(c);
  last_cell_ = new_cells.empty() ? c0 : new_cells.back();
  if (out_new_cells) *out_new_cells = new_cells;
  return vp;
}

Vec3 Delaunay::circumcenter(Cid c) const {
  const auto& cc = cells_[c];
  const Vec3& a = points_[cc.v[0]];
  const Vec3& b = points_[cc.v[1]];
  const Vec3& d = points_[cc.v[2]];
  const Vec3& e = points_[cc.v[3]];
  // Solve M x' = rhs where rows of M are (b-a),(d-a),(e-a) and
  // rhs = 0.5*(|b-a|^2, |d-a|^2, |e-a|^2); circumcenter = a + x'.
  Vec3 r0 = b - a, r1 = d - a, r2 = e - a;
  Vec3 rhs{0.5 * norm2(r0), 0.5 * norm2(r1), 0.5 * norm2(r2)};
  auto det3 = [](const Vec3& u, const Vec3& v, const Vec3& w) {
    return u.x * (v.y * w.z - v.z * w.y) - u.y * (v.x * w.z - v.z * w.x) +
           u.z * (v.x * w.y - v.y * w.x);
  };
  double det = det3(r0, r1, r2);
  if (det == 0) return a;  // degenerate
  double invdet = 1.0 / det;
  // Cramer: replace column k of M with rhs. Column entries: col0=(r0.x,r1.x,r2.x) etc.
  double dx = det3({rhs.x, r0.y, r0.z}, {rhs.y, r1.y, r1.z}, {rhs.z, r2.y, r2.z});
  double dy = det3({r0.x, rhs.x, r0.z}, {r1.x, rhs.y, r1.z}, {r2.x, rhs.z, r2.z});
  double dz = det3({r0.x, r0.y, rhs.x}, {r1.x, r1.y, rhs.y}, {r2.x, r2.y, rhs.z});
  return a + Vec3{dx * invdet, dy * invdet, dz * invdet};
}

double Delaunay::squared_circumradius(Cid c) const {
  Vec3 cc = circumcenter(c);
  return dist2(cc, points_[cells_[c].v[0]]);
}

bool Delaunay::verify_topology(std::string* err) const {
  auto fail = [&](const std::string& m) {
    if (err) *err = m;
    return false;
  };
  for (Cid c = 0; c < static_cast<Cid>(cells_.size()); ++c) {
    if (!cells_[c].alive) continue;
    const auto& cc = cells_[c];
    if (orient3d(points_[cc.v[0]], points_[cc.v[1]], points_[cc.v[2]],
                 points_[cc.v[3]]) != Sign::POSITIVE)
      return fail("cell not positively oriented: " + std::to_string(c));
    for (int i = 0; i < 4; ++i) {
      Cid o = cc.nbr[i];
      if (o == NO_CELL) continue;
      if (!cells_[o].alive) return fail("neighbor dead");
      int oi = facet_index_of_neighbor(o, c);
      if (oi < 0) return fail("neighbor not symmetric");
      std::array<Vid, 3> f = {cc.v[FACET[i][0]], cc.v[FACET[i][1]],
                              cc.v[FACET[i][2]]};
      std::array<Vid, 3> g = {cells_[o].v[FACET[oi][0]], cells_[o].v[FACET[oi][1]],
                              cells_[o].v[FACET[oi][2]]};
      for (Vid fv : f) {
        bool found = false;
        for (Vid gv : g) found |= (fv == gv);
        if (!found)
          return fail("shared facet vertex mismatch at cell " + std::to_string(c));
      }
    }
  }
  return true;
}

bool Delaunay::verify_delaunay(std::string* err) const {
  auto fail = [&](const std::string& m) {
    if (err) *err = m;
    return false;
  };
  int nv = num_vertices();
  for (Cid c = 0; c < static_cast<Cid>(cells_.size()); ++c) {
    if (!cells_[c].alive) continue;
    const auto& cc = cells_[c];
    if (cc.v[0] < 4 || cc.v[1] < 4 || cc.v[2] < 4 || cc.v[3] < 4) continue;
    for (Vid q = 4; q < nv; ++q) {
      if (q == cc.v[0] || q == cc.v[1] || q == cc.v[2] || q == cc.v[3]) continue;
      if (insphere(points_[cc.v[0]], points_[cc.v[1]], points_[cc.v[2]],
                   points_[cc.v[3]], points_[q]) == Sign::POSITIVE)
        return fail("empty-sphere violated: cell " + std::to_string(c) +
                    " contains vertex " + std::to_string(q));
    }
  }
  return true;
}

}  // namespace aw
