// Alpha wrapping with an offset. Given an input triangle soup and two
// parameters (alpha = carving-ball radius, offset = distance-field iso-level),
// produce a watertight, outward-oriented surface mesh that strictly encloses
// the input and stays within an O(alpha+offset) band of its offset surface.
//
// See DESIGN.md / docs/algorithm-spec.md for the algorithm.
#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "aabb_tree.hpp"
#include "delaunay.hpp"
#include "geom.hpp"

namespace aw {

struct Mesh {
  std::vector<Vec3> V;
  std::vector<std::array<int, 3>> F;  // outward-oriented triangles
};

struct WrapParams {
  double alpha = 0;    // absolute carving-ball radius
  double offset = 0;   // absolute offset (distance iso-level)
  bool manifold = true;
};

struct WrapStats {
  int steiner_points = 0;
  int rule1 = 0;
  int rule2 = 0;
  int carved = 0;
  int gates_popped = 0;
  int manifold_cells_reclaimed = 0;
  int output_vertices = 0;
  int output_faces = 0;
};

class AlphaWrap {
 public:
  // Run the wrap. `soup` may be non-manifold / self-intersecting / open.
  Mesh operator()(const std::vector<Triangle>& soup, const WrapParams& prm);

  const WrapStats& stats() const { return stats_; }

 private:
  enum Label : uint8_t { INSIDE = 0, OUTSIDE = 1, MANIFOLD = 2 };

  Oracle oracle_;
  Delaunay dt_;
  std::vector<uint8_t> label_;
  WrapParams prm_;
  WrapStats stats_;
  double alpha2_ = 0;
  Vid first_real_vertex_ = 0;  // ids < this are super/bbox scaffolding

  Label label_of(Cid c) const { return static_cast<Label>(label_[c]); }
  void set_label(Cid c, Label l) { label_[c] = l; }
  bool is_solid(Cid c) const { return label_[c] != OUTSIDE; }
  void ensure_label_capacity();

  bool facet_touches_scaffold(Cid c, int fi) const;
  // Squared radius of the smallest empty sphere through the gate facet
  // (crossing-aware); used vs alpha^2. Returns +inf for permissive gates.
  double gate_squared_radius(Cid outside, int fi, Cid inside) const;
  bool gate_traversable(Cid outside, int fi, Cid inside) const;

  // Outward unit normal of facet fi of cell c (pointing away from c's interior).
  Vec3 facet_outward_normal(Cid c, int fi) const;

  // Rule 1 / Rule 2 Steiner point. Returns false if the cell may be carved.
  bool compute_steiner_point(Cid outside, int fi, Cid inside, Vec3& out,
                             int& rule) const;

  void make_manifold();
  Mesh extract() const;
};

// Convenience wrapper: absolute parameters.
Mesh alpha_wrap(const std::vector<Triangle>& soup, double alpha, double offset,
                bool manifold = true, WrapStats* stats = nullptr);

}  // namespace aw
