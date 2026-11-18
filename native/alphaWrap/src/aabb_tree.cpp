#include "aabb_tree.hpp"

#include <algorithm>
#include <cmath>

namespace aw {

// ---------------------------------------------------------------------------
// Closest point on a triangle (Ericson, Real-Time Collision Detection).
// ---------------------------------------------------------------------------
Vec3 closest_point_on_triangle(const Vec3& p, const Vec3& a, const Vec3& b,
                               const Vec3& c) {
  Vec3 ab = b - a, ac = c - a, ap = p - a;
  double d1 = dot(ab, ap), d2 = dot(ac, ap);
  if (d1 <= 0 && d2 <= 0) return a;

  Vec3 bp = p - b;
  double d3 = dot(ab, bp), d4 = dot(ac, bp);
  if (d3 >= 0 && d4 <= d3) return b;

  double vc = d1 * d4 - d3 * d2;
  if (vc <= 0 && d1 >= 0 && d3 <= 0) {
    double v = d1 / (d1 - d3);
    return a + ab * v;
  }

  Vec3 cp = p - c;
  double d5 = dot(ab, cp), d6 = dot(ac, cp);
  if (d6 >= 0 && d5 <= d6) return c;

  double vb = d5 * d2 - d1 * d6;
  if (vb <= 0 && d2 >= 0 && d6 <= 0) {
    double w = d2 / (d2 - d6);
    return a + ac * w;
  }

  double va = d3 * d6 - d5 * d4;
  if (va <= 0 && (d4 - d3) >= 0 && (d5 - d6) >= 0) {
    double w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
    return b + (c - b) * w;
  }

  double denom = 1.0 / (va + vb + vc);
  double v = vb * denom, w = vc * denom;
  return a + ab * v + ac * w;
}

// ---------------------------------------------------------------------------
// Triangle vs solid tetrahedron: clip the triangle polygon against the tet's
// 4 half-spaces (Sutherland-Hodgman). Non-empty remainder => intersection.
// Inclusive on the boundary (touching counts as intersecting).
// ---------------------------------------------------------------------------
namespace {

// Clip convex polygon `poly` to the half-space { x : dot(n, x-p0)*keep >= -eps }.
void clip_halfspace(std::vector<Vec3>& poly, const Vec3& p0, const Vec3& n,
                    double keep, double eps) {
  if (poly.empty()) return;
  std::vector<Vec3> out;
  out.reserve(poly.size() + 1);
  int m = static_cast<int>(poly.size());
  for (int i = 0; i < m; ++i) {
    const Vec3& vi = poly[i];
    const Vec3& vj = poly[(i + 1) % m];
    double di = dot(n, vi - p0) * keep;
    double dj = dot(n, vj - p0) * keep;
    bool in_i = di >= -eps;
    bool in_j = dj >= -eps;
    if (in_i) out.push_back(vi);
    if (in_i != in_j) {
      double t = di / (di - dj);  // di,dj straddle 0
      out.push_back(vi + (vj - vi) * t);
    }
  }
  poly.swap(out);
}

}  // namespace

bool triangle_intersects_tet(const Vec3& t0, const Vec3& t1, const Vec3& t2,
                             const Vec3& a, const Vec3& b, const Vec3& c,
                             const Vec3& d) {
  std::vector<Vec3> poly = {t0, t1, t2};
  // Scale-relative tolerance.
  double scale = std::sqrt(std::max({norm2(b - a), norm2(c - a), norm2(d - a),
                                     1e-300}));
  double eps = 1e-12 * scale;

  const Vec3* faces[4][3] = {
      {&a, &b, &c}, {&a, &b, &d}, {&a, &c, &d}, {&b, &c, &d}};
  const Vec3* opp[4] = {&d, &c, &b, &a};
  for (int f = 0; f < 4; ++f) {
    const Vec3& fa = *faces[f][0];
    const Vec3& fb = *faces[f][1];
    const Vec3& fc = *faces[f][2];
    Vec3 n = cross(fb - fa, fc - fa);
    double keep = dot(n, *opp[f] - fa);  // sign of the inside (toward opp)
    if (keep == 0) continue;             // degenerate tet face; skip constraint
    keep = keep > 0 ? 1.0 : -1.0;
    clip_halfspace(poly, fa, n, keep, eps);
    if (poly.empty()) return false;
  }
  return !poly.empty();
}

// ---------------------------------------------------------------------------
// AABB tree
// ---------------------------------------------------------------------------
namespace {
Box tri_box(const Triangle& t) {
  Box b;
  b.expand(t[0]); b.expand(t[1]); b.expand(t[2]);
  return b;
}
Vec3 tri_centroid(const Triangle& t) { return (t[0] + t[1] + t[2]) / 3.0; }
bool boxes_overlap(const Box& x, const Box& y) {
  for (int i = 0; i < 3; ++i)
    if (x.hi[i] < y.lo[i] || y.hi[i] < x.lo[i]) return false;
  return true;
}
}  // namespace

void Oracle::build(std::vector<Triangle> tris_in) {
  // Drop degenerate (near-zero-area) triangles: they carry no distance/
  // intersection information and, left in, make the offset projection and
  // tet-intersection tests misbehave (a source of runaway refinement on
  // defective input). Scale the area threshold to the input size.
  Box bb;
  for (auto& t : tris_in) { bb.expand(t[0]); bb.expand(t[1]); bb.expand(t[2]); }
  double d = bb.diagonal();
  double area_eps = (d > 0 ? d * d : 1.0) * 1e-20;
  tris_.clear();
  tris_.reserve(tris_in.size());
  for (auto& t : tris_in) {
    double a2 = norm2(cross(t[1] - t[0], t[2] - t[0]));  // (2*area)^2
    if (a2 > area_eps) tris_.push_back(t);
  }
  order_.resize(tris_.size());
  for (int i = 0; i < static_cast<int>(tris_.size()); ++i) order_[i] = i;
  nodes_.clear();
  bbox_ = Box{};
  for (auto& t : tris_) { bbox_.expand(t[0]); bbox_.expand(t[1]); bbox_.expand(t[2]); }
  if (!tris_.empty()) build_node(0, static_cast<int>(tris_.size()), 0);
}

int Oracle::build_node(int start, int count, int depth) {
  int idx = static_cast<int>(nodes_.size());
  nodes_.emplace_back();
  Box box;
  for (int i = start; i < start + count; ++i) box.expand(tri_box(tris_[order_[i]]));
  const int LEAF = 4;
  if (count <= LEAF || depth > 60) {
    nodes_[idx].box = box;
    nodes_[idx].left = -1;
    nodes_[idx].start = start;
    nodes_[idx].count = count;
    return idx;
  }
  Vec3 ext = box.extent();
  int axis = 0;
  if (ext.y > ext.x) axis = 1;
  if (ext.z > ext[axis]) axis = 2;
  int mid = start + count / 2;
  std::nth_element(order_.begin() + start, order_.begin() + mid,
                   order_.begin() + start + count, [&](int u, int v) {
                     return tri_centroid(tris_[u])[axis] <
                            tri_centroid(tris_[v])[axis];
                   });
  int l = build_node(start, mid - start, depth + 1);
  int r = build_node(mid, start + count - mid, depth + 1);
  // emplace_back may have reallocated; re-fetch by index.
  nodes_[idx].box = box;
  nodes_[idx].left = l;
  nodes_[idx].start = r;  // right child index stored in `start` for internal nodes
  nodes_[idx].count = -1;
  return idx;
}

void Oracle::nearest_recursive(int node, const Vec3& p, double& best2,
                               Vec3& best) const {
  const Node& nd = nodes_[node];
  if (nd.box.dist2(p) >= best2) return;
  if (nd.left < 0) {  // leaf
    for (int i = nd.start; i < nd.start + nd.count; ++i) {
      const Triangle& t = tris_[order_[i]];
      Vec3 cp = closest_point_on_triangle(p, t[0], t[1], t[2]);
      double d2 = dist2(p, cp);
      if (d2 < best2) { best2 = d2; best = cp; }
    }
    return;
  }
  int lc = nd.left, rc = nd.start;
  double dl = nodes_[lc].box.dist2(p), dr = nodes_[rc].box.dist2(p);
  if (dl <= dr) {
    nearest_recursive(lc, p, best2, best);
    nearest_recursive(rc, p, best2, best);
  } else {
    nearest_recursive(rc, p, best2, best);
    nearest_recursive(lc, p, best2, best);
  }
}

double Oracle::squared_distance(const Vec3& p) const {
  double best2 = std::numeric_limits<double>::infinity();
  Vec3 best;
  if (!nodes_.empty()) nearest_recursive(0, p, best2, best);
  return best2;
}
double Oracle::unsigned_distance(const Vec3& p) const {
  return std::sqrt(squared_distance(p));
}
Vec3 Oracle::closest_point(const Vec3& p) const {
  double best2 = std::numeric_limits<double>::infinity();
  Vec3 best = p;
  if (!nodes_.empty()) nearest_recursive(0, p, best2, best);
  return best;
}

bool Oracle::intersect_tet_recursive(int node, const Box& qbox, const Vec3& a,
                                     const Vec3& b, const Vec3& c,
                                     const Vec3& d) const {
  const Node& nd = nodes_[node];
  if (!boxes_overlap(nd.box, qbox)) return false;
  if (nd.left < 0) {  // leaf
    for (int i = nd.start; i < nd.start + nd.count; ++i) {
      const Triangle& t = tris_[order_[i]];
      if (triangle_intersects_tet(t[0], t[1], t[2], a, b, c, d)) return true;
    }
    return false;
  }
  // Early exit: stop at the first intersecting triangle found in either child.
  return intersect_tet_recursive(nd.left, qbox, a, b, c, d) ||
         intersect_tet_recursive(nd.start, qbox, a, b, c, d);
}

bool Oracle::do_intersect_tet(const Vec3& a, const Vec3& b, const Vec3& c,
                              const Vec3& d) const {
  if (nodes_.empty()) return false;
  Box qbox;
  qbox.expand(a); qbox.expand(b); qbox.expand(c); qbox.expand(d);
  return intersect_tet_recursive(0, qbox, a, b, c, d);
}

bool Oracle::first_offset_crossing(const Vec3& a, const Vec3& b, double delta,
                                   Vec3& out) const {
  if (nodes_.empty()) return false;
  auto f = [&](double t) {
    Vec3 x = a + (b - a) * t;
    return unsigned_distance(x) - delta;
  };
  double seg_len = dist(a, b);
  if (seg_len == 0) return false;

  // Any point farther than `delta` outside the input bbox has distance > delta,
  // so a crossing can only occur where the segment is within the bbox inflated
  // by delta. Clip the marched interval [tlo,thi] to that region (huge speedup
  // for long outer-cell rays). Slab method.
  Vec3 dir = b - a;
  double tlo = 0.0, thi = 1.0;
  for (int k = 0; k < 3; ++k) {
    double lo = bbox_.lo[k] - delta, hi = bbox_.hi[k] + delta;
    double d = dir[k];
    if (std::fabs(d) < 1e-300) {
      if (a[k] < lo || a[k] > hi) return false;  // segment never enters slab
    } else {
      double t1 = (lo - a[k]) / d, t2 = (hi - a[k]) / d;
      if (t1 > t2) std::swap(t1, t2);
      tlo = std::max(tlo, t1);
      thi = std::min(thi, t2);
    }
  }
  if (tlo > thi) return false;  // segment misses the inflated bbox entirely

  // Sphere tracing: f(t) = dist(x(t), input) - delta is 1-Lipschitz in arclength,
  // so |f(t)| is a lower bound on the distance from x(t) to the delta-iso along
  // the ray. Stepping by f(t) never overshoots the first crossing, and converges
  // in O(log) steps regardless of how small delta is (vs O(L/delta) for a fixed
  // march). We march from the outside end (t=tlo, f>0) toward the inside end.
  double tol = std::max(delta * 1e-4, seg_len * 1e-9);
  double t = tlo;
  double ft = f(t);
  if (ft <= 0) { out = a + dir * t; return true; }  // already inside at entry
  const int max_iter = 200;
  for (int i = 0; i < max_iter; ++i) {
    // Safe forward step (never crosses the iso): advance arclength by ft.
    double dt = ft / seg_len;
    if (dt < tol) dt = tol;  // avoid stalling exactly at grazing
    t += dt;
    if (t >= thi) {
      // Check the endpoint in case the crossing is right at thi.
      double fe = f(thi);
      if (fe <= 0) { out = a + dir * thi; return true; }
      return false;
    }
    ft = f(t);
    if (ft <= tol) {  // reached the iso-surface (within tolerance)
      out = a + dir * t;
      return true;
    }
  }
  return false;  // grazing / no clean crossing within the iteration budget
}

}  // namespace aw
