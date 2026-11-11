// Incremental 3D Delaunay triangulation via Bowyer-Watson, built on exact
// predicates. Uses an enclosing super-tetrahedron of 4 far vertices so every
// real insertion is strictly inside the hull (all conflict cells finite).
//
// Cell/facet conventions:
//   - A cell stores 4 vertex ids v[0..3] with orient3d(p0,p1,p2,p3)==POSITIVE.
//   - Facet i is the triangle opposite v[i]; nbr[i] is the cell sharing it.
//   - "Outer" cells are those incident to a super-vertex; they model CGAL's
//     infinite cells (the exterior region to flood from during carving).
//
// Degeneracy handling: cospherical points (insphere == ZERO) are treated as
// not-in-conflict, a deterministic rule that yields a valid triangulation on
// cospherical/coplanar inputs (cubes, grids, points-on-faces — all covered by
// tests). The one residual failure mode (a point exactly coplanar with a
// conflict-zone boundary facet, which would spawn a zero-volume cell) is rare
// and caught by verify_topology(); full simulation-of-simplicity can be layered
// on in_conflict() if a real input ever triggers it.
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "geom.hpp"

namespace aw {

using Vid = int32_t;   // vertex id
using Cid = int32_t;   // cell id
constexpr Cid NO_CELL = -1;

struct Cell {
  std::array<Vid, 4> v{-1, -1, -1, -1};
  std::array<Cid, 4> nbr{NO_CELL, NO_CELL, NO_CELL, NO_CELL};
  bool alive = false;
};

class Delaunay {
 public:
  // Local vertex indices of the 3 vertices of each facet, ordered so the triple
  // has an outward normal (opposite vertex on its negative side). Public so the
  // wrap layer can reason about facets consistently.
  static constexpr int FACET[4][3] = {{1, 2, 3}, {0, 3, 2}, {0, 1, 3}, {0, 2, 1}};

  // Build the enclosing super-tetrahedron. `domain` must contain every point
  // that will ever be inserted; the super-tet is placed `margin` box-diagonals
  // away so real points stay strictly interior.
  void init(const Box& domain, double margin = 1000.0);

  // Insert a real point (must be strictly inside the super-tet). Returns its
  // vertex id. Duplicate points (coincident with an existing vertex) are
  // detected and return the existing id without modifying the triangulation.
  // If `new_cells` is non-null it receives the ids of cells created by this
  // insertion (empty on a duplicate).
  Vid insert(const Vec3& p, std::vector<Cid>* new_cells = nullptr);

  // ---- accessors ----
  int num_vertices() const { return static_cast<int>(points_.size()); }
  int num_cells() const { return static_cast<int>(cells_.size()); }  // includes dead
  int num_live_cells() const { return live_cell_count_; }
  const Vec3& point(Vid v) const { return points_[v]; }
  const Cell& cell(Cid c) const { return cells_[c]; }
  bool cell_alive(Cid c) const { return cells_[c].alive; }

  // The 4 super-tet vertices are ids 0..3.
  bool is_super_vertex(Vid v) const { return v < 4; }
  bool cell_is_outer(Cid c) const {
    const auto& cc = cells_[c];
    return cc.v[0] < 4 || cc.v[1] < 4 || cc.v[2] < 4 || cc.v[3] < 4;
  }
  bool is_finite_vertex(Vid v) const { return v >= 4; }

  // Cell circumcenter (inexact construction). Undefined for degenerate cells.
  Vec3 circumcenter(Cid c) const;
  // Squared circumradius of a cell (inexact).
  double squared_circumradius(Cid c) const;

  // Locate the cell containing p by walking from an optional hint. Returns a
  // live cell that contains p (in closure). p must be inside the super-tet.
  Cid locate(const Vec3& p, Cid hint = NO_CELL) const;

  // ---- validation (used by tests) ----
  // Neighbor symmetry + each internal facet shared by two cells with matching
  // vertex sets, and every live cell positively oriented.
  bool verify_topology(std::string* err = nullptr) const;
  // Empty-sphere (Delaunay) property over all cells whose 4 vertices are finite.
  bool verify_delaunay(std::string* err = nullptr) const;

 private:
  std::vector<Vec3> points_;
  std::vector<Cell> cells_;
  std::vector<Cid> free_cells_;
  int live_cell_count_ = 0;
  mutable Cid last_cell_ = NO_CELL;  // walk hint cache
  std::vector<uint32_t> mark_;       // per-cell BFS stamp (conflict-zone)
  uint32_t mark_ctr_ = 0;

  Cid new_cell();
  void kill_cell(Cid c);
  // True iff p is strictly inside cell c's circumsphere (SoS-free; ZERO -> false).
  bool in_conflict(Cid c, const Vec3& p) const;
  int facet_index_of_neighbor(Cid c, Cid neighbor) const;
};

}  // namespace aw
