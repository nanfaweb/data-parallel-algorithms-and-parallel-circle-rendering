// Benchmark for Parts 3 and 4.
//
// Usage: ./render_bench [size] [runs] [threads] [scenes]
//   size     image width and height in pixels, 1 to 4096, default 512
//   runs     number of timed runs per measurement, default 5
//   threads  comma separated thread counts, default 1,2,4,8
//   scenes   comma separated scene names, default dense,sparse,overlap,clustered
//
// Examples:
//   ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered
//   OMP_SCHEDULE="dynamic,8" ./render_bench 512 5 1,2,4,8 clustered
//
// For every scene the program measures the serial reference, the baseline
// parallel renderer (render_parallel) and the optimized renderer
// (render_optimized). Each parallel image is compared with the reference at
// every thread count before any time is recorded. A failed comparison skips the
// timings for that renderer and scene, and the program exits with status 1.
// No images are written, so no file output is ever timed.
//
// OMP_SCHEDULE only has an effect on loops written with schedule(runtime).
#include "renderer.h"
#include "scenes.h"
#include "../common/timing.h"
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {
struct Variant {
    const char* name;
    Image (*render)(int, int, const std::vector<Circle>&);
};
}  // namespace

int main(int argc, char** argv) {
    const int size = argc > 1 ? std::atoi(argv[1]) : 512;
    const int runs = argc > 2 ? std::atoi(argv[2]) : 5;
    const std::vector<int> threads = usable_threads(parse_list(argc > 3 ? argv[3] : "1,2,4,8"));
    const std::vector<std::string> scenes = argc > 4 ? split_names(argv[4]) : scene_names();
    if (size <= 0 || size > 4096 || runs < 1 || scenes.empty()) {
        std::cerr << "usage: ./render_bench [size 1..4096] [runs] [threads] [scenes]\n";
        return 2;
    }

    const Variant variants[] = {{"baseline", render_parallel}, {"optimized", render_optimized}};

    print_context(runs);
    print_header();
    int status = 0;

    for (const std::string& scene : scenes) {
        std::vector<Circle> circles;
        if (!make_scene(scene, circles)) {
            std::cerr << "unknown scene '" << scene << "', choose from:";
            for (const std::string& name : scene_names()) std::cerr << " " << name;
            std::cerr << "\n";
            return 2;
        }
        const std::string label = scene + "_" + std::to_string(size);
        const Image reference = render_reference(size, size, circles);

        const double serial_ms = median_ms(
            [&] { Image img = render_reference(size, size, circles); (void)img; }, runs);
        print_serial_row(label, "reference", serial_ms);

        for (const Variant& v : variants) {
            double t1_ms = 0.0;
            for (int p : threads) {
                omp_set_num_threads(p);
                if (!images_close(reference, v.render(size, size, circles))) {
                    std::printf("# %s %s FAIL at %d threads, timings skipped\n",
                                label.c_str(), v.name, p);
                    status = 1;
                    break;
                }
                const double ms = median_ms(
                    [&] { Image img = v.render(size, size, circles); (void)img; }, runs);
                if (p == 1) t1_ms = ms;
                print_parallel_row(label, v.name, p, ms, t1_ms, serial_ms);
            }
        }
    }
    return status;
}
