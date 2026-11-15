// Additional edge case tests for Parts 1 to 4 (student added, not part of the starter).
//
// Build: make edge_tests   (or the last line of build.sh)
// Run:   ./edge_tests            (each test is repeated at 1, 2, 3, 4, 7 and 8 threads)
//
// Every parallel result is compared with the unchanged serial reference.
#include "../saxpy/saxpy.h"
#include "../scan/scan.h"
#include "../render/renderer.h"
#include "../render/scenes.h"
#include "../common/rng.h"
#include <cmath>
#include <cstdio>
#include <omp.h>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
int failures = 0, checks = 0;
void check(bool ok, const std::string& what) {
    ++checks;
    if (!ok) { ++failures; std::printf("FAIL %s\n", what.c_str()); }
}
const int kThreads[] = {1, 2, 3, 4, 7, 8};

// ---------------- Part 1 ----------------
void test_saxpy() {
    // Sizes 0, 1, below the thread count, and not divisible by any thread count.
    for (size_t n : {0u, 1u, 2u, 3u, 7u, 13u, 1001u, 65537u}) {
        std::vector<float> x(n), y(n);
        Lcg rng(n + 7);
        for (size_t i = 0; i < n; ++i) { x[i] = rng.range(-5, 5); y[i] = rng.range(-5, 5); }
        auto ref = saxpy_serial(-1.75f, x, y);
        for (int p : kThreads) {
            omp_set_num_threads(p);
            auto out = saxpy_parallel(-1.75f, x, y);
            bool ok = out.size() == ref.size();
            for (size_t i = 0; ok && i < n; ++i) ok = out[i] == ref[i];
            check(ok, "saxpy n=" + std::to_string(n) + " p=" + std::to_string(p));
        }
    }
    // Mismatched sizes must throw, just like the reference.
    bool threw = false;
    try { saxpy_parallel(1.0f, std::vector<float>(3), std::vector<float>(4)); }
    catch (const std::invalid_argument&) { threw = true; }
    check(threw, "saxpy size mismatch throws");
}

// ---------------- Part 2 ----------------
void scan_case(const std::vector<int>& in, const std::string& name) {
    for (int p : kThreads) {
        omp_set_num_threads(p);
        check(exclusive_scan_parallel(in) == exclusive_scan_serial(in),
              "scan " + name + " p=" + std::to_string(p));
        check(find_repeats_parallel(in) == find_repeats_serial(in),
              "repeats " + name + " p=" + std::to_string(p));
    }
}
void test_scan() {
    // Examples from the assignment text.
    check(exclusive_scan_parallel({1, 4, 6, 8, 2}) == std::vector<int>({0, 1, 5, 11, 19}),
          "scan handout example");
    check(find_repeats_parallel({1, 2, 2, 1, 1, 1, 3, 5, 3, 3}) == std::vector<int>({1, 3, 4, 8}),
          "repeats handout example");
    // Lengths named in the assignment plus a few more awkward ones, random values.
    for (size_t n : {0u, 1u, 2u, 3u, 7u, 8u, 9u, 31u, 33u, 1023u, 1024u, 1025u, 4097u, 100003u}) {
        Lcg rng(1000 + n);
        std::vector<int> in(n);
        for (auto& v : in) v = rng.next_int(3);
        scan_case(in, "random n=" + std::to_string(n));
    }
    // Negative values, all equal (every position repeats), and no repeats at all.
    std::vector<int> neg(777), same(1025, 5), none(1025);
    Lcg rng(99);
    for (auto& v : neg) v = rng.next_int(5) - 2;
    for (size_t i = 0; i < none.size(); ++i) none[i] = int(i);
    scan_case(neg, "negative n=777");
    scan_case(same, "all-equal n=1025");
    scan_case(none, "no-repeats n=1025");
}

// ---------------- Parts 3 and 4 ----------------
void render_case(int w, int h, const std::vector<Circle>& circles, const std::string& name) {
    Image ref = render_reference(w, h, circles);
    for (int p : kThreads) {
        omp_set_num_threads(p);
        check(images_close(ref, render_parallel(w, h, circles)),
              "render_parallel " + name + " p=" + std::to_string(p));
        check(images_close(ref, render_optimized(w, h, circles)),
              "render_optimized " + name + " p=" + std::to_string(p));
    }
}
void test_render() {
    // Empty scene: every pixel must stay white.
    render_case(64, 64, {}, "no circles");
    // 1x1 image and a non-square image with sizes that do not divide the tile size.
    std::vector<Circle> dense;
    make_scene("dense", dense);
    render_case(1, 1, dense, "1x1 dense");
    render_case(37, 113, dense, "37x113 dense");
    // Circles partly or fully outside the image and one with zero radius.
    render_case(100, 80,
                {{-0.1f, 0.5f, 0.3f, 1, 0, 0, 0.5f}, {1.05f, 1.05f, 0.2f, 0, 1, 0, 0.7f},
                 {2.0f, 2.0f, 0.1f, 0, 0, 1, 0.9f}, {0.5f, 0.5f, 0.0f, 0, 0, 0, 1.0f}},
                "outside and zero radius");
    // Circles whose edge passes exactly through pixel centers (x = 0.5 / 8 steps).
    render_case(8, 8, {{0.5f, 0.5f, 0.25f, 1, 0, 0, 0.5f}, {0.5625f, 0.5625f, 0.125f, 0, 0, 1, 0.5f}},
                "edges on pixel centers");
    // Hand-checked order example from the report: A=(1,0,0,0.5), B=(0,0,1,0.5) over white.
    std::vector<Circle> ab = {{0.5f, 0.5f, 1.0f, 1, 0, 0, 0.5f}, {0.5f, 0.5f, 1.0f, 0, 0, 1, 0.5f}};
    std::vector<Circle> ba = {ab[1], ab[0]};
    omp_set_num_threads(4);
    Pixel pab = render_optimized(1, 1, ab).pixels[0], pba = render_optimized(1, 1, ba).pixels[0];
    check(pab.r == 0.5f && pab.g == 0.25f && pab.b == 0.75f, "A then B gives (0.5, 0.25, 0.75)");
    check(pba.r == 0.75f && pba.g == 0.25f && pba.b == 0.5f, "B then A gives (0.75, 0.25, 0.5)");
    // All named scenes at a size that is not a multiple of the tile size.
    for (const std::string& s : scene_names()) {
        std::vector<Circle> c;
        make_scene(s, c);
        render_case(200, 200, c, s + " 200x200");
    }
}
}  // namespace

int main() {
    test_saxpy();
    test_scan();
    test_render();
    std::printf("edge tests: %d checks, %d failures -> %s\n", checks, failures,
                failures ? "FAIL" : "PASS");
    return failures ? 1 : 0;
}
