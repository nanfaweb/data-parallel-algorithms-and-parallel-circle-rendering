// Measurements and counts used in the report (student added, not part of the starter).
//   1. Serial allocation cost vs SAXPY kernel bandwidth (Part 1).
//   2. Serial image allocation + white fill cost (Part 4 Amdahl term).
//   3. Work model counts per scene at 512x512 (Part 4): covers() tests done by
//      the baseline, tile-circle box tests and covers() tests done by the
//      optimized renderer, and per-tile work imbalance with 32x32 tiles.
// Build: make analysis_probe     Run: ./analysis_probe
#include "../common/timing.h"
#include "../render/renderer.h"
#include "../render/scenes.h"
#include <algorithm>
#include <cmath>
#include <vector>

int main() {
    const long long n = 10000000;
    std::vector<float> x(n, 1.f), y(n, 2.f), out(n, 0.f);
    const double alloc = median_ms([&] { std::vector<float> o(n, 0.f); (void)o; }, 7);
    std::printf("alloc+zero-fill 1e7 floats (serial): %.3f ms\n", alloc);
    for (int p : {1, 2, 4, 8}) {
        omp_set_num_threads(p);
        const double k = median_ms([&] {
            #pragma omp parallel for schedule(static)
            for (long long i = 0; i < n; ++i) out[i] = 2.5f * x[i] + y[i];
        }, 7);
        std::printf("saxpy kernel only, preallocated output, p=%d: %.3f ms (%.1f GB/s at 12 B/elem)\n",
                    p, k, 12.0 * n / k / 1e6);
    }
    const double img = median_ms([&] {
        Image im{512, 512, std::vector<Pixel>(512 * 512, Pixel{1, 1, 1})}; (void)im; }, 7);
    std::printf("512x512 image alloc+white fill (serial): %.3f ms\n", img);

    // Work model counts. Box formula mirrors pixel_box() in renderer.cpp.
    const int W = 512, H = 512, T = 32, tx = (W + T - 1) / T, ty = (H + T - 1) / T;
    std::printf("\nscene      circles  baseline_tests  tile_box_tests  opt_covers_tests  "
                "reduction  tile_work_max/mean  busiest_8th_share\n");
    for (const std::string& s : scene_names()) {
        std::vector<Circle> cs;
        make_scene(s, cs);
        long long covers_tests = 0;
        std::vector<long long> tile_work(tx * ty, 0);
        for (const Circle& c : cs) {
            auto lo = [](float v) { return std::max(0, int(std::floor(v)) - 1); };
            auto hi = [](float v, int m) { return std::min(m - 1, int(std::ceil(v)) + 1); };
            int x0 = lo((c.x - c.r) * W - 0.5f), x1 = hi((c.x + c.r) * W - 0.5f, W);
            int y0 = lo((c.y - c.r) * H - 0.5f), y1 = hi((c.y + c.r) * H - 0.5f, H);
            if (x0 > x1 || y0 > y1) continue;
            covers_tests += (long long)(x1 - x0 + 1) * (y1 - y0 + 1);
            for (int yy = y0; yy <= y1; ++yy)
                for (int xx = x0; xx <= x1; ++xx) tile_work[(yy / T) * tx + xx / T]++;
        }
        long long sum = 0, mx = 0;
        for (long long w : tile_work) { sum += w; mx = std::max(mx, w); }
        // Share of all work in the most loaded of 8 equal contiguous tile blocks (static schedule).
        long long best = 0, per = (tx * ty) / 8;
        for (int b = 0; b < 8; ++b) {
            long long s8 = 0;
            for (int t = b * per; t < (b + 1) * per; ++t) s8 += tile_work[t];
            best = std::max(best, s8);
        }
        const long long base = (long long)cs.size() * W * H;
        std::printf("%-10s %7zu %15lld %15lld %17lld %9.1fx %19.2f %18.2f\n", s.c_str(), cs.size(),
                    base, (long long)tx * ty * (long long)cs.size(), covers_tests,
                    double(base) / std::max(1LL, covers_tests), double(mx) / (double(sum) / (tx * ty)),
                    double(best) / std::max(1LL, sum));
    }
}
