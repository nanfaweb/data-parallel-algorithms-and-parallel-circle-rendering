# PDC Assignment 3 starter code

This is a CPU and OpenMP adaptation of three connected parallel programming exercises: SAXPY, exclusive prefix sum with repeat compaction, and a circle renderer. The serial versions are provided for comparison and you complete the parallel functions. The starter is intentionally incomplete. Until you finish the functions, the demos report FAIL and the benchmarks report the failed comparison and skip their timings.

## Requirements

A C++17 compiler with OpenMP support. Linux or WSL with `g++` is recommended. On macOS, use an OpenMP enabled compiler, for example Homebrew LLVM with `libomp`.

## Build and run

From this folder:

```sh
make
./saxpy_demo 1000000
./scan_demo 1025
./render_demo 256
```

Set the worker count from outside the program, for example `OMP_NUM_THREADS=4 ./saxpy_demo 1000000`. Your functions should not set the thread count themselves.

`make check` runs the three demos and returns a failure until the student functions are completed. `make bench` runs the three benchmark programs with their default settings. `make clean` removes the executables and every generated `render_*.ppm` image. Run it before you create your submission zip.

## Demo programs

The demos check correctness on one input and print a single run timing. That timing is a diagnostic only. Do not use it as benchmark data.

* `./saxpy_demo [n]` compares `saxpy_parallel` with `saxpy_serial` for n elements, default 1000000.
* `./scan_demo [n]` compares both Part 2 functions with the serial versions for n elements, default 1025. Run it with the lengths listed in the assignment (0, 1, 7, 8, 9, 1024 and 1025).
* `./render_demo [size] [scene] [variant]` renders one scene at size by size pixels and compares the parallel image with the reference. The scene is one of `dense`, `sparse`, `overlap` or `clustered` (default `dense`). The variant is `parallel` for `render_parallel` (Part 3) or `optimized` for `render_optimized` (Part 4), and the default is `parallel`. It writes `render_<scene>_reference.ppm` and `render_<scene>_<variant>.ppm`.

Examples:

```sh
./render_demo 512 sparse
./render_demo 512 clustered optimized
```

## Benchmark programs

The benchmarks produce the tables for your performance report. Each one compares the parallel result with the serial reference at every thread count before it records a time, so a wrong answer never produces a timing row.

```sh
./saxpy_bench 5 1,2,4,8 10000,1000000,10000000
./scan_bench 5 1,2,4,8 100000,10000000
./render_bench 512 5 1,2,4,8 sparse,overlap,clustered
```

The arguments are, in order:

* `saxpy_bench [runs] [threads] [sizes]` where sizes are array lengths.
* `scan_bench [runs] [threads] [sizes]` where sizes are array lengths. It measures both the scan and the repeat compaction.
* `render_bench [size] [runs] [threads] [scenes]` where size is the image width and height. It measures the serial reference, the baseline parallel renderer and the optimized renderer on each scene.

Every argument is optional and the defaults are the values shown above, except that `scan_bench` uses two sizes and `render_bench` uses all four scenes at size 512.

Each program prints a header with the compiler, the OpenMP version, the number of processors, the schedule setting and the measurement rules, followed by one row per measurement. The columns are:

* `input` and `op` describe what was measured.
* `variant` is `serial` or `parallel`, and `threads` is the worker count.
* `median_ms` is the median of the timed runs after one warmup run.
* `speedup` is T1 divided by Tp, where T1 is the parallel code on one thread. `efficiency` is speedup divided by the thread count.
* `vs_serial` is the serial reference time divided by Tp.

Thread counts larger than the number of available processors are skipped and a note is printed, because the assignment asks for them only where the machine supports them. The one thread run is always included because it defines T1.

To compare OpenMP schedules, write your main renderer loop with `schedule(runtime)` and select the schedule from outside:

```sh
OMP_SCHEDULE="static" ./render_bench 512 5 1,2,4,8 clustered
OMP_SCHEDULE="dynamic,8" ./render_bench 512 5 1,2,4,8 clustered
```

Copy the printed rows into your report together with the header lines, since those lines contain the machine details the report must state.

## Scenes

The scenes are generated from fixed seeds, so every machine produces the same circles and the same images.

* `dense` has 40 circles on a regular grid with moderate overlap.
* `sparse` has 300 small circles scattered over the image. Most pixels are covered by no circle.
* `overlap` has 150 large low opacity circles near the middle. Many circles cover each central pixel.
* `clustered` has 500 small circles, most of them packed into two hot spots. The work per tile is very uneven.

The generators are in `render/scenes.cpp`. You may add scenes of your own there if you need them.

## Files and responsibilities

* `Makefile` builds the three demos and the three benchmarks.
* `common/timing.h` has the median timing, thread list handling and table printing used by the benchmarks.
* `common/rng.h` has a small deterministic random number generator used for scenes and benchmark inputs.
* `saxpy/saxpy.h` declares the SAXPY functions.
* `saxpy/saxpy.cpp` has the correct serial SAXPY and the unfinished parallel SAXPY.
* `saxpy/main.cpp` is the SAXPY demo.
* `saxpy/bench.cpp` is the SAXPY benchmark.
* `scan/scan.h` declares the prefix sum and repeated index functions.
* `scan/scan.cpp` has the correct serial versions and the two student TODO functions.
* `scan/main.cpp` is the scan demo.
* `scan/bench.cpp` is the scan and compaction benchmark.
* `render/renderer.h` has the circle, pixel and image types and the renderer interface.
* `render/renderer.cpp` has the sequential blending reference, the unfinished `render_parallel` and `render_optimized`, the PPM writer and the image comparator.
* `render/scenes.h` and `render/scenes.cpp` generate the named scenes.
* `render/main.cpp` is the renderer demo.
* `render/bench.cpp` is the renderer benchmark.

## Required student work

1. Complete `saxpy_parallel` using an OpenMP parallel loop.
2. Complete `exclusive_scan_parallel` using parallel stages and safe synchronization.
3. Complete `find_repeats_parallel` with flags, prefix sum offsets and scatter.
4. Complete `render_parallel`, preserving each pixel's circle blending order.
5. Complete `render_optimized` with bounding box culling or ordered tile candidate lists, without changing image semantics.

Do not change declarations, the serial reference functions, `images_close`, or the correctness comparisons in the demos. You may add helper functions in the corresponding `.cpp` file. Add your own edge case tests as separate files and list the commands for them in your own README, as described in the assignment PDF. Run at least five measurements per experiment and report the machine and compiler.

## Notes on the renderer

The image is normalized to the coordinates [0, 1]. Each pixel is sampled at its center. Circles are blended in input order, using the supplied alpha equation. The stub functions return a white image on purpose, so passing the comparison requires a correct implementation.

When you add bounding boxes in Part 4, keep using the `covers()` test in `renderer.cpp` to decide coverage and treat the box only as a filter. A pixel whose center lies almost exactly on a circle edge can change from covered to not covered after a small rounding difference, and that changes its color by far more than the comparison tolerance.
