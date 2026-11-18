// AABB tree over an input triangle soup, and the geometric "oracle" the wrap
// algorithm queries against the input: unsigned distance, closest point,
// tetrahedron-soup intersection, and segment-vs-offset-isosurface crossing.
// Dependency-free; commercial-safe.
#pragma once

#include <vector>

#include "geom.hpp"

namespace aw {

// Closest point to `p` on triangle (a,b,c). Exposed for testing.
Vec3 closest_point_on_triangle(const Vec3& p, const Vec3& a, const Vec3& b,
                               const Vec3& c);

// Does triangle (t0,t1,t2) intersect the solid tetrahedron (a,b,c,d)?
bool triangle_intersects_tet(const Vec3& t0, const Vec3& t1, const Vec3& t2,
                             const Vec3& a, const Vec3& b, const Vec3& c,
                             const Vec3& d);

class Oracle {
 public:
  void build(std::vector<Triangle> tris);

  bool empty() const { return tris_.empty(); }
  const Box& bbox() const { return bbox_; }
  int num_triangles() const { return static_cast<int>(tris_.size()); }

  // Squared / unsigned Euclidean distance from p to the soup.
  double squared_distance(const Vec3& p) const;
  double unsigned_distance(const Vec3& p) const;
  // Closest point on the soup to p.
  Vec3 closest_point(const Vec3& p) const;

  // Does the solid tetrahedron (a,b,c,d) intersect any input triangle?
  bool do_intersect_tet(const Vec3& a, const Vec3& b, const Vec3& c,
                        const Vec3& d) const;

  // First point along segment [a,b] (marching from a) where the unsigned
  // distance field crosses the level `delta`. Returns true and sets `out` on a
  // crossing; false if the whole segment stays on one side of `delta`.
  bool first_offset_crossing(const Vec3& a, const Vec3& b, double delta,
                             Vec3& out) const;

 private:
  struct Node {
    Box box;
    int left = -1;    // child node index, or -1 for leaf
    int start = 0;    // leaf: first triangle in order_
    int count = 0;    // leaf: triangle count
  };

  std::vector<Triangle> tris_;
  std::vector<int> order_;   // triangle indices, permuted by the tree
  std::vector<Node> nodes_;
  Box bbox_;

  int build_node(int start, int count, int depth);
  void nearest_recursive(int node, const Vec3& p, double& best2,
                         Vec3& best) const;
  bool intersect_tet_recursive(int node, const Box& qbox, const Vec3& a,
                               const Vec3& b, const Vec3& c, const Vec3& d) const;
};

}  // namespace aw
