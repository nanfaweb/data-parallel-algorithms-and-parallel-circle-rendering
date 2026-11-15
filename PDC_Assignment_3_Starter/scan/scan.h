#pragma once
#include <vector>

// Part 2. Exclusive prefix sum and compaction of repeated positions.

// Exclusive sum: output[i] holds the sum of input[0] up to input[i minus 1],
// and output[0] is 0. For [1, 4, 6, 8, 2] the result is [0, 1, 5, 11, 19].
// The result has the same length as the input. An empty input gives an empty result.
// Sequential reference. Do not change it.
std::vector<int> exclusive_scan_serial(const std::vector<int>& input);
// Parallel version that you complete in scan.cpp.
std::vector<int> exclusive_scan_parallel(const std::vector<int>& input);

// Returns every position i where input[i] equals input[i + 1], in ascending
// order. For [1, 2, 2, 1, 1, 1, 3, 5, 3, 3] the result is [1, 3, 4, 8].
// Inputs with fewer than two elements give an empty result.
// Sequential reference. Do not change it.
std::vector<int> find_repeats_serial(const std::vector<int>& input);
// Parallel version that you complete in scan.cpp. It should use
// exclusive_scan_parallel or the same scan technique on a 0/1 flag array.
std::vector<int> find_repeats_parallel(const std::vector<int>& input);
