#pragma once
// Timing and reporting helpers shared by the three benchmark programs.
//
// Conventions used by every benchmark in this assignment:
//   * Each measurement is the median of several runs after one warmup run.
//   * T1 is the parallel implementation run with one thread. The serial
//     reference is reported separately in its own row.
//   * speedup = T1 / Tp and efficiency = speedup / p.
//   * vs_serial = serial reference time / Tp.
//   * Writing output files is never part of a timed region.
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <omp.h>
#include <sstream>
#include <string>
#include <vector>

// Wall clock time of one call to fn, in milliseconds.
template <class F>
double time_once_ms(F&& fn) {
    auto start = std::chrono::steady_clock::now();
    fn();
    auto stop = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(stop - start).count();
}

// Median of a list of samples. The list must not be empty.
inline double median_of(std::vector<double> samples) {
    std::sort(samples.begin(), samples.end());
    size_t mid = samples.size() / 2;
    return samples.size() % 2 ? samples[mid] : 0.5 * (samples[mid - 1] + samples[mid]);
}

// Runs fn untimed for the warmup runs, then times it for the requested number
// of runs and returns the median in milliseconds.
template <class F>
double median_ms(F&& fn, int runs, int warmups = 1) {
    for (int i = 0; i < warmups; ++i) fn();
    std::vector<double> samples;
    for (int i = 0; i < runs; ++i) samples.push_back(time_once_ms(fn));
    return median_of(samples);
}

// Splits a comma separated list of numbers such as "1,2,4,8".
inline std::vector<unsigned long long> parse_list(const std::string& text) {
    std::vector<unsigned long long> values;
    std::stringstream in(text);
    std::string item;
    while (std::getline(in, item, ','))
        if (!item.empty()) values.push_back(std::strtoull(item.c_str(), nullptr, 10));
    return values;
}

// Splits a comma separated list of names such as "sparse,overlap".
inline std::vector<std::string> split_names(const std::string& text) {
    std::vector<std::string> names;
    std::stringstream in(text);
    std::string item;
    while (std::getline(in, item, ','))
        if (!item.empty()) names.push_back(item);
    return names;
}

// Turns a requested list of thread counts into the list that will be measured.
// One thread is always included and always first because it defines T1. Counts
// larger than the number of processors are skipped, since the assignment asks
// for thread counts only where the machine supports them.
inline std::vector<int> usable_threads(const std::vector<unsigned long long>& requested) {
    const int procs = omp_get_num_procs();
    std::vector<int> result{1};
    for (unsigned long long p : requested) {
        if (p <= 1) continue;
        if (p > static_cast<unsigned long long>(procs)) {
            std::printf("# note: %llu threads skipped, only %d processors available\n", p, procs);
            continue;
        }
        if (std::find(result.begin(), result.end(), static_cast<int>(p)) == result.end())
            result.push_back(static_cast<int>(p));
    }
    std::sort(result.begin(), result.end());
    return result;
}

// Prints the machine and measurement details that the report needs.
inline void print_context(int runs) {
    std::printf("# compiler %s\n", __VERSION__);
    std::printf("# OpenMP version macro %d\n", _OPENMP);
    std::printf("# processors available %d, default maximum threads %d\n",
                omp_get_num_procs(), omp_get_max_threads());
    const char* schedule = std::getenv("OMP_SCHEDULE");
    std::printf("# OMP_SCHEDULE %s\n", schedule ? schedule : "not set");
    std::printf("# medians of %d runs after one warmup run, file output is never timed\n", runs);
    std::printf("# T1 is the parallel code on one thread, speedup = T1 / Tp, efficiency = speedup / p\n");
    std::printf("# vs_serial = serial reference time / Tp\n");
}

inline void print_header() {
    std::printf("%-16s %-10s %-9s %7s %12s %9s %11s %10s\n", "input", "op", "variant",
                "threads", "median_ms", "speedup", "efficiency", "vs_serial");
}

// Row for the serial reference. Speedup and efficiency do not apply to it.
inline void print_serial_row(const std::string& input, const std::string& op, double serial_ms) {
    std::printf("%-16s %-10s %-9s %7d %12.4f %9s %11s %10.3f\n", input.c_str(), op.c_str(),
                "serial", 1, serial_ms, "n/a", "n/a", 1.0);
}

// Row for a parallel measurement at a given thread count.
inline void print_parallel_row(const std::string& input, const std::string& op, int threads,
                               double ms, double t1_ms, double serial_ms) {
    const double speedup = t1_ms / ms;
    std::printf("%-16s %-10s %-9s %7d %12.4f %9.3f %11.3f %10.3f\n", input.c_str(), op.c_str(),
                "parallel", threads, ms, speedup, speedup / threads, serial_ms / ms);
}
