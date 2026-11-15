#pragma once
#include <vector>

// A filled circle with a translucent color.
//
// The image is normalized so that both x and y run over [0, 1]. The center
// (x, y) and the radius r use those units, so on a square image the circle is
// round and r is a fraction of the image width. The color components red,
// green and blue and the opacity alpha all lie in [0, 1].
// Circle order matters because alpha blending is not commutative.
struct Circle {float x,y,r,red,green,blue,alpha;};

// One pixel color with components in [0, 1].
struct Pixel {float r,g,b;};

// A width by height image stored row by row. Pixel (x, y) is pixels[y * width + x].
struct Image {int width,height;std::vector<Pixel> pixels;};

// Sequential reference. Draws the circles in their given order onto a white
// background. Do not change it.
Image render_reference(int width,int height,const std::vector<Circle>& circles);

// Part 3. Parallel renderer that you complete in renderer.cpp. It must match
// render_reference within the tolerance of images_close for every scene.
Image render_parallel(int width,int height,const std::vector<Circle>& circles);

// Part 4. Optimized parallel renderer that you complete in renderer.cpp. It has
// the same contract as render_parallel, but should avoid circle and pixel
// tests that cannot change the result.
Image render_optimized(int width,int height,const std::vector<Circle>& circles);

// True when the images have the same size and every color component differs by
// at most the tolerance.
bool images_close(const Image& a,const Image& b,float tolerance=0.0001f);

// Writes the image as a text PPM file. Throws std::runtime_error when the file
// cannot be opened.
void save_ppm(const Image& image,const char* path);
