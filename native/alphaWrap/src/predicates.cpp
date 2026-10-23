#include "predicates.hpp"

extern "C" {
namespace predicates {
double orient3d(const double* pa, const double* pb, const double* pc,
                const double* pd);
double insphere(const double* pa, const double* pb, const double* pc,
                const double* pd, const double* pe);
double orient3dfast(const double* pa, const double* pb, const double* pc,
                    const double* pd);
}  // namespace predicates
}  // extern "C"

namespace aw {

namespace {
inline Sign sign_of(double v) {
  if (v > 0) return Sign::POSITIVE;
  if (v < 0) return Sign::NEGATIVE;
  return Sign::ZERO;
}
}  // namespace

Sign orient3d(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d) {
  // Shewchuk's orient3d returns the sign of det[a-d; b-d; c-d] = (a-d).((b-d)x(c-d)),
  // which is the negation of our convention (scalar triple product of edges
  // from a). Flip so the reference tet a,b,c,d = e0,e1,e2,e3 yields POSITIVE.
  const double r = predicates::orient3d(a.data(), b.data(), c.data(), d.data());
  return sign_of(-r);
}

Sign insphere(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d,
              const Vec3& e) {
  // Shewchuk's insphere returns a value whose sign means "e inside" only when
  // (a,b,c,d) is positively oriented *in Shewchuk's convention*; if negatively
  // oriented the sign is flipped. Multiplying by Shewchuk's own orient3d sign
  // yields an orientation-independent "inside > 0" result. Both raw calls use
  // the same (Shewchuk) convention, so the product is self-consistent.
  const double ins = predicates::insphere(a.data(), b.data(), c.data(),
                                          d.data(), e.data());
  if (ins == 0.0) return Sign::ZERO;
  const double o = predicates::orient3d(a.data(), b.data(), c.data(), d.data());
  return sign_of(ins * o);
}

double orient3d_fast(const Vec3& a, const Vec3& b, const Vec3& c, const Vec3& d) {
  return -predicates::orient3dfast(a.data(), b.data(), c.data(), d.data());
}

}  // namespace aw
