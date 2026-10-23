// Exact geometric predicates for the alpha-wrap implementation.
//
// Thin, convention-normalized wrappers over Shewchuk's adaptive-precision
// predicates (danshapero/predicates fork, public domain). We fix a single sign
// convention here and pin it with unit tests so the rest of the codebase never
// has to reason about Shewchuk's raw conventions.
#pragma once

#include "geom.hpp"

namespace aw {

enum class Sign : int { NEGATIVE = -1, ZERO = 0, POSITIVE = 1 };

inline int to_int(Sign s) { return static_cast<int>(s); }

// orient3d(a,b,c,d):
//   POSITIVE  if d is on the positive side of the oriented plane (a,b,c), i.e.
//             the scalar triple product (b-a) . ((c-a) x (d-a)) > 0, which is
//             +1 for the reference tetrahedron a=(0,0,0) b=(1,0,0) c=(0,1,0)
//             d=(0,0,1). Equivalently, (a,b,c,d) is a positively oriented tet.
//   NEGATIVE  if d is on the negative side.
//   ZERO      if a,b,c,d are coplanar.
// Exact.
Sign orient3d(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d);

// insphere(a,b,c,d,e):
//   POSITIVE  if e lies strictly inside the sphere through a,b,c,d,
//   NEGATIVE  if strictly outside,
//   ZERO      if exactly cospherical.
// Convention is independent of the orientation of (a,b,c,d): the result is
// normalized by the orientation sign, so callers may pass the four tet vertices
// in any order. Exact (returns ZERO on exact cospherical input; symbolic
// perturbation for Delaunay is layered on top of this in delaunay.cpp).
Sign insphere(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d,
              const Vec3& e);

// Non-robust fast variants (used only where an approximate answer is
// acceptable, e.g. spatial heuristics). Return a raw double sign.
double orient3d_fast(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d);

}  // namespace aw
