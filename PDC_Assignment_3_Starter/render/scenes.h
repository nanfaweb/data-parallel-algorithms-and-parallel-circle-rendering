#pragma once
// Deterministic circle scenes for the correctness checks and the performance
// experiments in Parts 3 and 4. The same name always gives the same circles on
// every machine, so images and timings can be compared and reproduced.
#include "renderer.h"
#include <string>
#include <vector>

// Names of all available scenes, in the order dense, sparse, overlap, clustered.
//
//   dense      40 circles on a regular grid with moderate overlap. This is the
//              scene used by render_demo by default.
//   sparse     300 small circles scattered over the image. Most pixels are not
//              covered by any circle, so culling has a lot to skip.
//   overlap    150 large circles with low opacity near the middle of the image.
//              Many circles cover each central pixel, so the blending work per
//              pixel is high and culling skips little.
//   clustered  500 small circles, most of them packed into two hot spots with a
//              few scattered over the rest. Work per tile is very uneven, which
//              is what the static and dynamic schedule comparison needs.
std::vector<std::string> scene_names();

// Fills circles with the named scene, replacing its previous contents.
// Returns false and leaves circles unchanged when the name is not recognised.
bool make_scene(const std::string& name, std::vector<Circle>& circles);
