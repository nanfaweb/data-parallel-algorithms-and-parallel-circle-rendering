// Part 1: sequential reference and the OpenMP exercise.
#include "saxpy.h"
#include <stdexcept>

// Reference implementation. Every parallel result is compared against this one.
std::vector<float> saxpy_serial(float a, const std::vector<float>& x,
                                const std::vector<float>& y) {
    if (x.size() != y.size()) throw std::invalid_argument("SAXPY sizes differ");
    std::vector<float> out(x.size());
    for (size_t i = 0; i < x.size(); ++i) out[i] = a * x[i] + y[i];
    return out;
}

// Your implementation goes here.
std::vector<float> saxpy_parallel(float a, const std::vector<float>& x,
                                  const std::vector<float>& y) {
    if (x.size() != y.size()) throw std::invalid_argument("SAXPY sizes differ");
    // The constructor below fills the output with zeros on a single thread.
    // That serial step is part of the measured time and is worth remembering
    // when you explain your efficiency numbers in the report.
    std::vector<float> out(x.size(), 0.0f);
    // Static work-sharing: each thread gets one contiguous block of indices, so
    // every out[i] is written exactly once by exactly one thread and the output
    // order is the input order. A signed loop index keeps the loop canonical
    // for OpenMP; n == 0 simply runs zero iterations.
    const long long n = static_cast<long long>(x.size());
    const float* xp = x.data();
    const float* yp = y.data();
    float* op = out.data();
    #pragma omp parallel for schedule(static)
    for (long long i = 0; i < n; ++i) op[i] = a * xp[i] + yp[i];
    return out;
}
