// Benchmark for Part 1.
//
// Usage: ./saxpy_bench [runs] [threads] [sizes]
//   runs     number of timed runs per measurement, default 5
//   threads  comma separated thread counts, default 1,2,4,8
//   sizes    comma separated array lengths, default 10000,1000000,10000000
//
// Example: ./saxpy_bench 5 1,2,4,8 10000,1000000,10000000
//
// For every size and thread count the parallel result is compared with the
// serial reference before any time is recorded. If the comparison fails, the
// program reports it, skips the timings for that size, and exits with status 1.
// The inputs are the same as in saxpy_demo, so results are reproducible.
// The timed region includes allocating the output vector, because both
// implementations do that inside the function.
#include "saxpy.h"
#include "../common/timing.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {
bool same_values(const std::vector<float>& a, const std::vector<float>& b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); ++i)
        if (std::abs(a[i] - b[i]) > 0.0001f) return false;
    return true;
}
}  // namespace

int main(int argc, char** argv) {
    const int runs = argc > 1 ? std::atoi(argv[1]) : 5;
    const std::vector<int> threads = usable_threads(parse_list(argc > 2 ? argv[2] : "1,2,4,8"));
    const std::vector<unsigned long long> sizes =
        parse_list(argc > 3 ? argv[3] : "10000,1000000,10000000");
    if (runs < 1 || sizes.empty()) {
        std::cerr << "usage: ./saxpy_bench [runs] [threads] [sizes]\n";
        return 2;
    }

    const float a = 2.5f;
    print_context(runs);
    print_header();
    int status = 0;

    for (unsigned long long n : sizes) {
        std::vector<float> x(n), y(n);
        for (size_t i = 0; i < n; ++i) { x[i] = float(i % 97) / 10; y[i] = float(i % 17); }
        const std::vector<float> expected = saxpy_serial(a, x, y);
        const std::string label = "n=" + std::to_string(n);

        const double serial_ms = median_ms([&] { auto r = saxpy_serial(a, x, y); (void)r; }, runs);
        print_serial_row(label, "saxpy", serial_ms);

        double t1_ms = 0.0;
        for (int p : threads) {
            omp_set_num_threads(p);
            if (!same_values(expected, saxpy_parallel(a, x, y))) {
                std::printf("# %s FAIL at %d threads, timings skipped\n", label.c_str(), p);
                status = 1;
                break;
            }
            const double ms = median_ms([&] { auto r = saxpy_parallel(a, x, y); (void)r; }, runs);
            if (p == 1) t1_ms = ms;
            print_parallel_row(label, "saxpy", p, ms, t1_ms, serial_ms);
        }
    }
    return status;
}
