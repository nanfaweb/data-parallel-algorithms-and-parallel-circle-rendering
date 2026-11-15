// Parts 3 and 4: point in circle coverage and ordered alpha blending.
#include "renderer.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <stdexcept>
namespace {

// Applies one circle to one pixel: new = alpha * color + (1 minus alpha) * old,
// computed separately for the red, green and blue components.
void blend(Pixel& p,const Circle& c) {
    p.r=c.alpha*c.red+(1-c.alpha)*p.r;
    p.g=c.alpha*c.green+(1-c.alpha)*p.g;
    p.b=c.alpha*c.blue+(1-c.alpha)*p.b;
}

// A pixel is covered when its center lies inside the circle, boundary included.
// The center of pixel (x, y) is ((x + 0.5) / w, (y + 0.5) / h) in the
// normalized coordinates of the image.
bool covers(const Circle& c,int x,int y,int w,int h) {
    float px=(x+0.5f)/w, py=(y+0.5f)/h;
    float dx=px-c.x,dy=py-c.y;
    return dx*dx+dy*dy<=c.r*c.r;
}
}

// Reference renderer. It visits the circles in order and, for each circle,
// every pixel of the image, so its cost is proportional to circles times pixels.
Image render_reference(int width,int height,const std::vector<Circle>& circles) {
    Image image{width,height,std::vector<Pixel>(width*height,Pixel{1,1,1})};
    for (const Circle& c : circles)
        for (int y=0;y<height;++y)
            for (int x=0;x<width;++x)
                if(covers(c,x,y,width,height)) blend(image.pixels[y*width+x],c);
    return image;
}

// Part 3. Your implementation goes here. You may add helper functions above it.
Image render_parallel(int width,int height,const std::vector<Circle>& circles) {
    Image image{width,height,std::vector<Pixel>(width*height,Pixel{1,1,1})};
    // TODO: assign independent pixels or tiles to OpenMP workers. For every
    // pixel, apply the circles in their original input order using covers()
    // and blend(). Two workers must never write the same pixel.
    // Do not call render_reference here and do not set the thread count in
    // this function. Consider writing the main loop with schedule(runtime) so
    // that OMP_SCHEDULE can change the schedule in the Part 4 experiments.
    (void)circles;
    return image;
}

// Part 4. Your implementation goes here.
Image render_optimized(int width,int height,const std::vector<Circle>& circles) {
    Image image{width,height,std::vector<Pixel>(width*height,Pixel{1,1,1})};
    // TODO: produce the same image as render_parallel while skipping work that
    // cannot change the result. Use either a bounding box for each circle or an
    // ordered list of candidate circles for each tile, and state which one you
    // chose in the report.
    // Rules to follow:
    //   * Circles must reach every pixel in their original input order. Do not
    //     sort the circles.
    //   * Coverage is still decided by covers(). A bounding box is only a
    //     filter. Pad it by at least one pixel on every side, because rounding
    //     in floating point can place a pixel center right at the circle edge.
    //   * Time spent building boxes or candidate lists counts as part of the
    //     renderer, so keep it inside this function.
    (void)circles;
    return image;
}

// Compares two images component by component against the tolerance.
bool images_close(const Image& a,const Image& b,float t) {
    if(a.width!=b.width||a.height!=b.height||a.pixels.size()!=b.pixels.size())return false;
    for(size_t i=0;i<a.pixels.size();++i) {
        const Pixel& x=a.pixels[i];const Pixel& y=b.pixels[i];
        if(std::abs(x.r-y.r)>t||std::abs(x.g-y.g)>t||std::abs(x.b-y.b)>t)return false;
    }
    return true;
}

// Writes the image as a text PPM. Each component is clamped to [0, 1] and
// scaled to 0 through 255.
void save_ppm(const Image& image,const char* path) {
    std::ofstream file(path);
    if(!file)throw std::runtime_error("Cannot open PPM output file");
    file<<"P3\n"<<image.width<<" "<<image.height<<"\n255\n";
    for(const Pixel& p:image.pixels) {
        auto ch=[](float x){return int(std::round(std::max(0.0f,std::min(1.0f,x))*255));};
        file<<ch(p.r)<<" "<<ch(p.g)<<" "<<ch(p.b)<<"\n";
    }
}
