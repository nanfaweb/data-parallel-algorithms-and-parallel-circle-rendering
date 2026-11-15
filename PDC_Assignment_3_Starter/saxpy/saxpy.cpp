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
    // TODO: compute out with an OpenMP parallel for loop.
    // Each element must be written exactly once and by exactly one thread.
    // Do not call saxpy_serial here. Do not set the thread count in this
    // function, the demo and benchmark programs control it from outside.
    (void)a;
    return out;
}
