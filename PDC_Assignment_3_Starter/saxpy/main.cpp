// Demo for Part 1. Runs the serial reference and the parallel version once on
// the same input, compares them, and prints a single run timing.
//
// Usage: ./saxpy_demo [n]       (n defaults to 1000000)
// Thread count: OMP_NUM_THREADS=4 ./saxpy_demo 1000000
//
// The single run timings printed here are only a quick diagnostic. Use
// ./saxpy_bench for the measurements that go into the report.
#include "saxpy.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>
int main(int argc, char** argv) {
    size_t n = argc > 1 ? std::strtoull(argv[1], nullptr, 10) : 1000000;
    std::vector<float> x(n), y(n);
    for (size_t i = 0; i < n; ++i) { x[i] = float(i % 97) / 10; y[i] = float(i % 17); }
    auto t0 = std::chrono::steady_clock::now();
    auto ref = saxpy_serial(2.5f, x, y);
    auto t1 = std::chrono::steady_clock::now();
    auto out = saxpy_parallel(2.5f, x, y);
    auto t2 = std::chrono::steady_clock::now();
    bool ok = true;
    for (size_t i = 0; i < n; ++i) if (std::abs(ref[i]-out[i]) > 0.0001f) {ok=false;break;}
    std::cout << "SAXPY N=" << n << " serial_ms="
      << std::chrono::duration<double,std::milli>(t1-t0).count()
      << " parallel_ms=" << std::chrono::duration<double,std::milli>(t2-t1).count()
      << " correctness=" << (ok ? "PASS" : "FAIL (complete TODO)") << "\n";
    return ok ? 0 : 1;
}
