#pragma once
// Small deterministic random number generator used to build reproducible inputs.
//
// The standard library distributions are avoided on purpose. Their output can
// differ between compilers and operating systems, which would give different
// scenes and arrays on different machines and make results hard to compare.
#include <cstdint>

class Lcg {
public:
    explicit Lcg(std::uint64_t seed) : state_(seed) {}

    // Next value in the half open range [0, 1).
    float next_float() {
        advance();
        return float((state_ >> 40) & 0xFFFFFF) / 16777216.0f;
    }

    // Next value in the half open range [lo, hi).
    float range(float lo, float hi) { return lo + (hi - lo) * next_float(); }

    // Next integer in the range 0 to bound minus one. The bound must be positive.
    int next_int(int bound) {
        advance();
        return int((state_ >> 33) % std::uint64_t(bound));
    }

private:
    void advance() { state_ = state_ * 6364136223846793005ULL + 1442695040888963407ULL; }
    std::uint64_t state_;
};
