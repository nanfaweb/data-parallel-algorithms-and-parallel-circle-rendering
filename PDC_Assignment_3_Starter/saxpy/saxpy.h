#pragma once
#include <vector>

// Part 1. Elementwise operation: output[i] = a * x[i] + y[i].
//
// Both functions return a new vector of the same length as the inputs and do
// not modify their inputs. Both throw std::invalid_argument when x and y have
// different sizes. Empty inputs are valid and give an empty result.

// Sequential reference. Do not change it.
std::vector<float> saxpy_serial(float a, const std::vector<float>& x,
                                const std::vector<float>& y);

// OpenMP version that you complete in saxpy.cpp.
std::vector<float> saxpy_parallel(float a, const std::vector<float>& x,
                                  const std::vector<float>& y);
