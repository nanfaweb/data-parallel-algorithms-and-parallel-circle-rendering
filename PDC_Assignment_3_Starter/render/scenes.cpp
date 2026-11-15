// Scene generators. All randomness comes from the Lcg generator with a fixed
// seed per scene, so the output does not depend on the compiler or platform.
#include "scenes.h"
#include "../common/rng.h"

namespace {

// Builds a circle with a random color and an opacity in [alpha_lo, alpha_hi).
// The braces fix the order in which the random values are drawn.
Circle random_circle(Lcg& rng, float x, float y, float r, float alpha_lo, float alpha_hi) {
    return Circle{x, y, r, rng.next_float(), rng.next_float(), rng.next_float(),
                  rng.range(alpha_lo, alpha_hi)};
}

// Position offset with a rough bell shape, made by adding three uniform values.
// The result lies in the range minus spread to plus spread.
float bell_offset(Lcg& rng, float spread) {
    float sum = rng.next_float();
    sum += rng.next_float();
    sum += rng.next_float();
    return (sum - 1.5f) / 1.5f * spread;
}

void make_dense(std::vector<Circle>& circles) {
    for (int i = 0; i < 40; ++i)
        circles.push_back({0.2f + 0.6f * (i % 8) / 7, 0.2f + 0.6f * (i / 8) / 4,
                           0.09f + 0.025f * (i % 3),
                           float(i % 3 == 0), float(i % 3 == 1), float(i % 3 == 2), 0.35f});
}

void make_sparse(std::vector<Circle>& circles) {
    Lcg rng(1001);
    for (int i = 0; i < 300; ++i) {
        float x = rng.next_float();
        float y = rng.next_float();
        float r = rng.range(0.004f, 0.015f);
        circles.push_back(random_circle(rng, x, y, r, 0.4f, 0.9f));
    }
}

void make_overlap(std::vector<Circle>& circles) {
    Lcg rng(2002);
    for (int i = 0; i < 150; ++i) {
        float x = rng.range(0.15f, 0.85f);
        float y = rng.range(0.15f, 0.85f);
        float r = rng.range(0.15f, 0.35f);
        circles.push_back(random_circle(rng, x, y, r, 0.1f, 0.3f));
    }
}

void make_clustered(std::vector<Circle>& circles) {
    Lcg rng(3003);
    // Hot spot near the top left, hot spot near the lower right, then a few
    // circles spread over the whole image.
    for (int i = 0; i < 300; ++i) {
        float x = 0.25f + bell_offset(rng, 0.15f);
        float y = 0.25f + bell_offset(rng, 0.15f);
        float r = rng.range(0.01f, 0.04f);
        circles.push_back(random_circle(rng, x, y, r, 0.2f, 0.6f));
    }
    for (int i = 0; i < 100; ++i) {
        float x = 0.75f + bell_offset(rng, 0.1f);
        float y = 0.7f + bell_offset(rng, 0.1f);
        float r = rng.range(0.01f, 0.04f);
        circles.push_back(random_circle(rng, x, y, r, 0.2f, 0.6f));
    }
    for (int i = 0; i < 100; ++i) {
        float x = rng.next_float();
        float y = rng.next_float();
        float r = rng.range(0.01f, 0.03f);
        circles.push_back(random_circle(rng, x, y, r, 0.2f, 0.6f));
    }
}

}  // namespace

std::vector<std::string> scene_names() { return {"dense", "sparse", "overlap", "clustered"}; }

bool make_scene(const std::string& name, std::vector<Circle>& circles) {
    std::vector<Circle> built;
    if (name == "dense") make_dense(built);
    else if (name == "sparse") make_sparse(built);
    else if (name == "overlap") make_overlap(built);
    else if (name == "clustered") make_clustered(built);
    else return false;
    circles = built;
    return true;
}
