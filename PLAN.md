# PDC Assignment 3 — plan

Goal: complete PDC Assignment 3 (SAXPY, scan + repeat compaction, parallel circle
renderer, optimized renderer, MPI analysis) and submit code + report PDF.
Repo: https://github.com/nanfaweb/pdc-assignment-3 (private).

## Done
- Starter code imported.
- Part 1: saxpy_parallel (static omp for).
- Part 2: Blelloch exclusive scan + flag/scan/scatter repeats.
- Part 3: row-parallel render_parallel.
- Part 4: tiled bounding-box render_optimized.
- Edge tests (365 checks pass), benchmarks in docs/results.
- Report docs/RollNumber_Report.pdf (Parts 1–5) built by docs/make_report.py.

## Next
- Fill in name / roll number / section on the report title page (docs/make_report.py) and rebuild.
- Rename the report to <RollNumber>_Report.pdf, then `make clean` and zip as <RollNumber>_Assignment3.zip.
- Optional: confirm the build with `make` on Linux/WSL (only build.sh was run here, because make is not installed).
