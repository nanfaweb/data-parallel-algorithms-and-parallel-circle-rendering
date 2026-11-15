# PDC Assignment 3 — solution README

Exact commands used to compile, test and benchmark this solution. Run them from
`PDC_Assignment_3_Starter/`. Tested with GCC 15.2.0 (MinGW-w64) and libgomp on an
AMD Ryzen 7 7435HS (8 cores, 16 threads), Windows 11. Linux/WSL works the same way.

## Build

```sh
make            # demos, benchmarks, edge_tests and analysis_probe
# without make (same flags as the Makefile):
sh build.sh
```

## What was implemented

| Part | Function | Approach |
|------|----------|----------|
| 1 | `saxpy_parallel` (`saxpy/saxpy.cpp`) | `omp parallel for schedule(static)` |
| 2 | `exclusive_scan_parallel` (`scan/scan.cpp`) | Blelloch up-sweep/down-sweep in one parallel region, zero padding to the next power of two |
| 2 | `find_repeats_parallel` | flags, then a parallel exclusive scan, then a parallel scatter |
| 3 | `render_parallel` (`render/renderer.cpp`) | rows owned by single threads, circles in input order, `schedule(runtime)` |
| 4 | `render_optimized` | 32x32 tiles with per-circle bounding-box culling, circles walked in input order per tile, `schedule(runtime)` |

Starter declarations, the serial references, `images_close` and the demo comparisons are unchanged.

## Correctness

```sh
make check                                     # supplied demos
./saxpy_demo 0; ./saxpy_demo 7; ./saxpy_demo 1000000
for n in 0 1 7 8 9 1024 1025; do ./scan_demo $n; done
for s in dense sparse overlap clustered; do ./render_demo 512 $s parallel; ./render_demo 512 $s optimized; done
make test                                      # added edge tests (tests/edge_tests.cpp), 365 checks
```

The added edge tests cover all parts at 1, 2, 3, 4, 7 and 8 threads:
- SAXPY: empty, small, and non-divisible sizes, plus the size-mismatch exception.
- Scan and repeats: the handout examples, random and negative arrays, all-equal and no-repeat arrays, and lengths 0 to 100003.
- Renderer: empty scene, 1x1 and 37x113 images, circles outside the image, zero radius, circle edges on pixel centres, the A/B blend order example, and every scene at 200x200.

## Benchmarks (outputs saved in `../docs/results/`)

```sh
./saxpy_bench 7 1,2,4,8 10000,1000000,10000000
./scan_bench 7 1,2,4,8 100000,10000000
OMP_SCHEDULE="static"    ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered,dense
OMP_SCHEDULE="dynamic,1" ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered,dense
OMP_SCHEDULE="dynamic,8" ./render_bench 512 5 1,2,4,8 sparse,overlap,clustered
./analysis_probe        # serial-overhead probe and Part 4 work-model counts
```

## Report

`../docs/RollNumber_Report.pdf` is generated from the saved results:

```sh
python ../docs/make_report.py      # needs matplotlib and reportlab
```

## Submission zip

Run `make clean` first. Rename `RollNumber` to your roll number, then zip the code,
the report and this README as `RollNumber_Assignment3.zip`.
