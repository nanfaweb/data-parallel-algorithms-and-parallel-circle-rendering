#!/bin/sh
# Same compile commands as the Makefile, for machines without make.
set -e
CXX=${CXX:-g++}
F="-O2 -std=c++17 -Wall -Wextra -fopenmp"
$CXX $F saxpy/main.cpp saxpy/saxpy.cpp -o saxpy_demo
$CXX $F scan/main.cpp scan/scan.cpp -o scan_demo
$CXX $F render/main.cpp render/renderer.cpp render/scenes.cpp -o render_demo
$CXX $F saxpy/bench.cpp saxpy/saxpy.cpp -o saxpy_bench
$CXX $F scan/bench.cpp scan/scan.cpp -o scan_bench
$CXX $F render/bench.cpp render/renderer.cpp render/scenes.cpp -o render_bench
$CXX $F tests/edge_tests.cpp saxpy/saxpy.cpp scan/scan.cpp render/renderer.cpp render/scenes.cpp -o edge_tests
