# Builds the demo programs and the benchmark programs from the assignment root.
#
#   make          builds everything
#   make check    runs the three demos, fails until the TODO functions are done
#   make bench    runs the three benchmarks with their default settings
#   make clean    removes executables and generated images
CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -fopenmp

DEMOS = saxpy_demo scan_demo render_demo
BENCHES = saxpy_bench scan_bench render_bench
SHARED = common/timing.h common/rng.h

all: $(DEMOS) $(BENCHES)

saxpy_demo: saxpy/main.cpp saxpy/saxpy.cpp saxpy/saxpy.h
	$(CXX) $(CXXFLAGS) saxpy/main.cpp saxpy/saxpy.cpp -o $@

scan_demo: scan/main.cpp scan/scan.cpp scan/scan.h
	$(CXX) $(CXXFLAGS) scan/main.cpp scan/scan.cpp -o $@

render_demo: render/main.cpp render/renderer.cpp render/renderer.h render/scenes.cpp render/scenes.h common/rng.h
	$(CXX) $(CXXFLAGS) render/main.cpp render/renderer.cpp render/scenes.cpp -o $@

saxpy_bench: saxpy/bench.cpp saxpy/saxpy.cpp saxpy/saxpy.h $(SHARED)
	$(CXX) $(CXXFLAGS) saxpy/bench.cpp saxpy/saxpy.cpp -o $@

scan_bench: scan/bench.cpp scan/scan.cpp scan/scan.h $(SHARED)
	$(CXX) $(CXXFLAGS) scan/bench.cpp scan/scan.cpp -o $@

render_bench: render/bench.cpp render/renderer.cpp render/renderer.h render/scenes.cpp render/scenes.h $(SHARED)
	$(CXX) $(CXXFLAGS) render/bench.cpp render/renderer.cpp render/scenes.cpp -o $@

check: $(DEMOS)
	./saxpy_demo
	./scan_demo
	./render_demo

bench: $(BENCHES)
	./saxpy_bench
	./scan_bench
	./render_bench

clean:
	rm -f $(DEMOS) $(BENCHES) render_*.ppm

.PHONY: all check bench clean
