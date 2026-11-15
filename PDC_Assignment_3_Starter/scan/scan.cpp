// Part 2: reference scan and repeat compaction, followed by the two functions to complete.
#include "scan.h"
#include <vector>

// Reference implementations. Every parallel result is compared against these.
std::vector<int> exclusive_scan_serial(const std::vector<int>& input) {
    std::vector<int> result(input.size());
    int sum=0;
    for (size_t i=0;i<input.size();++i) {result[i]=sum;sum+=input[i];}
    return result;
}
std::vector<int> find_repeats_serial(const std::vector<int>& input) {
    std::vector<int> indices;
    for (size_t i=0;i+1<input.size();++i)
        if(input[i]==input[i+1]) indices.push_back(static_cast<int>(i));
    return indices;
}

// Your implementations go here. You may add helper functions above them.

// Work-efficient (Blelloch) exclusive scan done in place on a power-of-two
// buffer. Additions are done on unsigned values so that overflow wraps exactly
// like the serial int loop does in practice, without signed-overflow UB.
//
// One parallel region is opened for the whole scan. Each tree level is an
// "omp for" whose implicit barrier is the synchronization between stages:
// level d+1 reads values that level d wrote, so no thread may start a level
// before every thread has finished the previous one.
namespace {
void blelloch_scan_inplace(std::vector<unsigned>& buf) {
    const long long m = static_cast<long long>(buf.size());  // power of two
    unsigned* a = buf.data();
    #pragma omp parallel
    {
        // Up-sweep (reduce): after level d, a[k*2d + 2d - 1] holds the sum of
        // its 2d-element block.
        for (long long d = 1; d < m; d *= 2) {
            const long long stride = 2 * d;
            #pragma omp for schedule(static)
            for (long long k = 0; k < m / stride; ++k) {
                const long long i = k * stride;
                a[i + stride - 1] += a[i + d - 1];
            }
        }
        #pragma omp single
        a[m - 1] = 0;  // implicit barrier at the end of single
        // Down-sweep: push prefix sums back down the tree.
        for (long long d = m / 2; d >= 1; d /= 2) {
            const long long stride = 2 * d;
            #pragma omp for schedule(static)
            for (long long k = 0; k < m / stride; ++k) {
                const long long i = k * stride;
                const unsigned left = a[i + d - 1];
                a[i + d - 1] = a[i + stride - 1];
                a[i + stride - 1] += left;
            }
        }
    }
}

// Smallest power of two that is >= n (n >= 1).
size_t next_pow2(size_t n) {
    size_t m = 1;
    while (m < n) m *= 2;
    return m;
}
}  // namespace

std::vector<int> exclusive_scan_parallel(const std::vector<int>& input) {
    const size_t n = input.size();
    if (n == 0) return {};
    // Padding strategy: extend to the next power of two with zeros. Zero is the
    // identity of +, so the padded tail cannot change any of the first n
    // prefix sums; it is simply discarded at the end.
    std::vector<unsigned> buf(next_pow2(n), 0u);
    const long long nn = static_cast<long long>(n);
    #pragma omp parallel for schedule(static)
    for (long long i = 0; i < nn; ++i) buf[i] = static_cast<unsigned>(input[i]);
    blelloch_scan_inplace(buf);
    std::vector<int> result(n);
    #pragma omp parallel for schedule(static)
    for (long long i = 0; i < nn; ++i) result[i] = static_cast<int>(buf[i]);
    return result;
}

std::vector<int> find_repeats_parallel(const std::vector<int>& input) {
    if (input.size() < 2) return {};
    // 1. Flags: flag[i] = 1 when input[i] == input[i + 1], for i in [0, n - 2].
    const long long m = static_cast<long long>(input.size()) - 1;
    std::vector<int> flags(m);
    #pragma omp parallel for schedule(static)
    for (long long i = 0; i < m; ++i) flags[i] = input[i] == input[i + 1] ? 1 : 0;
    // 2. Exclusive scan of the flags gives each match its output slot.
    const std::vector<int> offsets = exclusive_scan_parallel(flags);
    const int total = offsets[m - 1] + flags[m - 1];
    // 3. Scatter. Offsets are strictly increasing over flagged positions, so
    //    every slot is written by exactly one i and the output is ascending.
    std::vector<int> out(total);
    #pragma omp parallel for schedule(static)
    for (long long i = 0; i < m; ++i)
        if (flags[i]) out[offsets[i]] = static_cast<int>(i);
    return out;
}
