// Demo for Part 2. Checks both parallel functions against the serial versions
// on one deterministic input.
//
// Usage: ./scan_demo [n]        (n defaults to 1025)
// Thread count: OMP_NUM_THREADS=4 ./scan_demo 1025
//
// Run it with the lengths named in the assignment (0, 1, 7, 8, 9, 1024, 1025)
// and add your own tests for other inputs, such as random arrays.
#include "scan.h"
#include <cstdlib>
#include <iostream>
#include <vector>
int main(int argc, char** argv) {
    size_t n=argc>1?std::strtoull(argv[1],nullptr,10):1025;
    std::vector<int> input(n);
    for(size_t i=0;i<n;++i) input[i]=static_cast<int>((i/3)%7);
    bool scan_ok=exclusive_scan_serial(input)==exclusive_scan_parallel(input);
    bool repeats_ok=find_repeats_serial(input)==find_repeats_parallel(input);
    std::cout << "SCAN N="<<n<<" scan="<<(scan_ok?"PASS":"FAIL (complete TODO)")
              <<" repeats="<<(repeats_ok?"PASS":"FAIL (complete TODO)")<<"\n";
    return scan_ok && repeats_ok ? 0 : 1;
}
