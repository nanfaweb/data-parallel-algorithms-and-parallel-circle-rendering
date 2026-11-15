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

// Inclusive pixel bounding box of a circle, clamped to the image. A pixel
// center (x + 0.5) / w lies in [cx - r, cx + r] only for x in
// [(cx - r) * w - 0.5, (cx + r) * w - 0.5]; the box is padded by one extra
// pixel on every side so rounding can never exclude a covered pixel. An empty
// box (x0 > x1 or y0 > y1) means the circle misses the image entirely.
struct Box {int x0,y0,x1,y1;};
Box pixel_box(const Circle& c,int w,int h) {
    // Clamp before converting to int so far-away circles cannot overflow.
    auto cl=[](float v){return std::max(-4.0f,std::min(v,1e7f));};
    auto lo=[&](float v){return std::max(0,int(std::floor(cl(v)))-1);};
    auto hi=[&](float v,int n){return std::min(n-1,int(std::ceil(cl(v)))+1);};
    const float r=std::max(c.r,0.0f);
    return Box{lo((c.x-r)*w-0.5f),lo((c.y-r)*h-0.5f),
               hi((c.x+r)*w-0.5f,w),hi((c.y+r)*h-0.5f,h)};
}

// Side length of the square tiles used by render_optimized.
constexpr int kTile=32;
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
    // Pixel-parallel decomposition by image rows. Each row belongs to exactly
    // one worker, so no pixel is ever written by two threads and no locks are
    // needed. Within a pixel the circles are applied in their input order, so
    // the blend sequence (and therefore every float result) is identical to
    // the reference, which only swaps the loop nesting.
    // schedule(runtime) lets OMP_SCHEDULE choose static/dynamic for Part 4.
    const int nc=static_cast<int>(circles.size());
    const Circle* cs=circles.data();
    Pixel* px=image.pixels.data();
    #pragma omp parallel for schedule(runtime)
    for (int y=0;y<height;++y)
        for (int x=0;x<width;++x) {
            Pixel p=px[y*width+x];  // keep the pixel in registers while blending
            for (int k=0;k<nc;++k)
                if(covers(cs[k],x,y,width,height)) blend(p,cs[k]);
            px[y*width+x]=p;
        }
    return image;
}

// Part 4. Your implementation goes here.
Image render_optimized(int width,int height,const std::vector<Circle>& circles) {
    Image image{width,height,std::vector<Pixel>(width*height,Pixel{1,1,1})};
    // Chosen approach: per-circle bounding boxes used as a filter inside an
    // ordered per-tile candidate pass.
    //   1. Compute each circle's pixel bounding box once (parallel over circles).
    //   2. Split the image into 32x32 tiles. Each tile is owned by exactly one
    //      worker (schedule(runtime) so OMP_SCHEDULE can pick static/dynamic).
    //   3. The owner walks the circles in their original order, skips every
    //      circle whose box misses the tile, and blends the rest only over the
    //      box-tile intersection. covers() still decides coverage.
    // Within a tile circles are the outer loop and go in input order, so every
    // pixel still receives its circles in input order; tiles are disjoint, so
    // no two workers write the same pixel. Nothing is sorted.
    const int nc=static_cast<int>(circles.size());
    if(nc==0||width<=0||height<=0) return image;
    std::vector<Box> boxes(nc);
    #pragma omp parallel for schedule(static)
    for (int k=0;k<nc;++k) boxes[k]=pixel_box(circles[k],width,height);

    const int tilesX=(width+kTile-1)/kTile, tilesY=(height+kTile-1)/kTile;
    const int ntiles=tilesX*tilesY;
    const Circle* cs=circles.data();
    const Box* bs=boxes.data();
    Pixel* px=image.pixels.data();
    #pragma omp parallel for schedule(runtime)
    for (int t=0;t<ntiles;++t) {
        const int tx0=(t%tilesX)*kTile, ty0=(t/tilesX)*kTile;
        const int tx1=std::min(tx0+kTile,width)-1, ty1=std::min(ty0+kTile,height)-1;
        for (int k=0;k<nc;++k) {
            const Box& b=bs[k];
            const int x0=std::max(b.x0,tx0), x1=std::min(b.x1,tx1);
            const int y0=std::max(b.y0,ty0), y1=std::min(b.y1,ty1);
            if(x0>x1||y0>y1) continue;  // circle cannot touch this tile
            const Circle& c=cs[k];
            for (int y=y0;y<=y1;++y)
                for (int x=x0;x<=x1;++x)
                    if(covers(c,x,y,width,height)) blend(px[y*width+x],c);
        }
    }
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
