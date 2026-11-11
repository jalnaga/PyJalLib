// Basic 3D geometry primitives shared across the alpha-wrap implementation.
// Header-only, dependency-free.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace aw {

struct Vec3 {
  double x = 0, y = 0, z = 0;

  Vec3() = default;
  Vec3(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}

  double        operator[](int i) const { return (&x)[i]; }
  double&       operator[](int i) { return (&x)[i]; }
  const double* data() const { return &x; }
};

inline Vec3 operator+(const Vec3& a, const Vec3& b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline Vec3 operator-(const Vec3& a, const Vec3& b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline Vec3 operator*(const Vec3& a, double s) { return {a.x * s, a.y * s, a.z * s}; }
inline Vec3 operator*(double s, const Vec3& a) { return a * s; }
inline Vec3 operator/(const Vec3& a, double s) { return {a.x / s, a.y / s, a.z / s}; }

inline double dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec3   cross(const Vec3& a, const Vec3& b) {
  return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
inline double norm2(const Vec3& a) { return dot(a, a); }
inline double norm(const Vec3& a) { return std::sqrt(norm2(a)); }
inline double dist2(const Vec3& a, const Vec3& b) { return norm2(a - b); }
inline double dist(const Vec3& a, const Vec3& b) { return std::sqrt(dist2(a, b)); }

// Axis-aligned bounding box.
struct Box {
  Vec3 lo{ std::numeric_limits<double>::infinity(),
           std::numeric_limits<double>::infinity(),
           std::numeric_limits<double>::infinity() };
  Vec3 hi{ -std::numeric_limits<double>::infinity(),
           -std::numeric_limits<double>::infinity(),
           -std::numeric_limits<double>::infinity() };

  void expand(const Vec3& p) {
    for (int i = 0; i < 3; ++i) {
      lo[i] = std::min(lo[i], p[i]);
      hi[i] = std::max(hi[i], p[i]);
    }
  }
  void expand(const Box& b) { expand(b.lo); expand(b.hi); }
  bool empty() const { return lo.x > hi.x; }
  Vec3 center() const { return (lo + hi) * 0.5; }
  Vec3 extent() const { return hi - lo; }
  double diagonal() const { return empty() ? 0.0 : norm(hi - lo); }

  // Squared distance from a point to the box (0 if inside).
  double dist2(const Vec3& p) const {
    double d2 = 0;
    for (int i = 0; i < 3; ++i) {
      double v = p[i];
      if (v < lo[i]) d2 += (lo[i] - v) * (lo[i] - v);
      else if (v > hi[i]) d2 += (v - hi[i]) * (v - hi[i]);
    }
    return d2;
  }
};

using Triangle = std::array<Vec3, 3>;

}  // namespace aw
