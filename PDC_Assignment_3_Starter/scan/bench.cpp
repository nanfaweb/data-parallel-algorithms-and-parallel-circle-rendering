// Benchmark for Part 2.
//
// Usage: ./scan_bench [runs] [threads] [sizes]
//   runs     number of timed runs per measurement, default 5
//   threads  comma separated thread counts, default 1,2,4,8
//   sizes    comma separated array lengths, default 100000,10000000
//
// Example: ./scan_bench 5 1,2,4,8 100000,10000000
//
// Both exclusive_scan_parallel and find_repeats_parallel are measured against
// their serial versions. Inputs are pseudo random integers in the range 0 to 3
// from a fixed seed, so about one position in four is a repeat and results are
// reproducible. Each parallel result is compared with the serial result before
// timing. A failed comparison skips the timings for that operation and size,
// and the program exits with status 1.
#include "scan.h"
#include "../common/rng.h"
#include "../common/timing.h"
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

// Measures one operation. serial and parallel are callables that take no
// arguments and return the result vector for the current input.
template <class Serial, class Parallel>
int bench_operation(const std::string& label, const std::string& op, Serial serial,
                    Parallel parallel, const std::vector<int>& threads, int runs) {
    const std::vector<int> expected = serial();
    const double serial_ms = median_ms([&] { auto r = serial(); (void)r; }, runs);
    print_serial_row(label, op, serial_ms);

    double t1_ms = 0.0;
    for (int p : threads) {
        omp_set_num_threads(p);
        if (parallel() != expected) {
            std::printf("# %s %s FAIL at %d threads, timings skipped\n", label.c_str(), op.c_str(), p);
            return 1;
        }
        const double ms = median_ms([&] { auto r = parallel(); (void)r; }, runs);
        if (p == 1) t1_ms = ms;
        print_parallel_row(label, op, p, ms, t1_ms, serial_ms);
    }
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    const int runs = argc > 1 ? std::atoi(argv[1]) : 5;
    const std::vector<int> threads = usable_threads(parse_list(argc > 2 ? argv[2] : "1,2,4,8"));
    const std::vector<unsigned long long> sizes = parse_list(argc > 3 ? argv[3] : "100000,10000000");
    if (runs < 1 || sizes.empty()) {
        std::cerr << "usage: ./scan_bench [runs] [threads] [sizes]\n";
        return 2;
    }

    print_context(runs);
    print_header();
    int status = 0;

    for (unsigned long long n : sizes) {
        Lcg rng(12345);
        std::vector<int> input(n);
        for (size_t i = 0; i < n; ++i) input[i] = rng.next_int(4);
        const std::string label = "n=" + std::to_string(n);

        status |= bench_operation(label, "scan",
                                  [&] { return exclusive_scan_serial(input); },
                                  [&] { return exclusive_scan_parallel(input); }, threads, runs);
        status |= bench_operation(label, "repeats",
                                  [&] { return find_repeats_serial(input); },
                                  [&] { return find_repeats_parallel(input); }, threads, runs);
    }
    return status;
}
