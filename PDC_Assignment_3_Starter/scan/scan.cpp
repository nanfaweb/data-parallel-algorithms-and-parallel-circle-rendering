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
std::vector<int> exclusive_scan_parallel(const std::vector<int>& input) {
    std::vector<int> result(input.size(),0);
    // TODO: implement a parallel exclusive scan with OpenMP.
    // Use separate stages (for example an up sweep followed by a down sweep)
    // with safe synchronization between them. A blocked approach with per
    // thread partial sums is also accepted if you explain it in the report.
    // Support empty arrays and lengths that are not powers of two.
    // Do not call exclusive_scan_serial or the standard library scan
    // algorithms, and do not set the thread count in this function.
    return result;
}
std::vector<int> find_repeats_parallel(const std::vector<int>& input) {
    // TODO: build a 0/1 flag array, scan it to get destination offsets, then
    // scatter each matching index to its offset in the output.
    // The output must be in ascending order and its length must be exactly the
    // number of repeated positions. Handle arrays of length 0 and 1.
    (void)input;
    return {};
}
