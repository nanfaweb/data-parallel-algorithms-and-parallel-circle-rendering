// Demo for Parts 3 and 4. Renders one scene with the serial reference and with
// one of the parallel renderers, writes both images, and compares them pixel by
// pixel.
//
// Usage: ./render_demo [size] [scene] [variant]
//   size     image width and height in pixels, 1 to 4096, default 256
//   scene    dense, sparse, overlap or clustered, default dense
//   variant  parallel (render_parallel) or optimized (render_optimized),
//            default parallel
//
// Examples:
//   ./render_demo 256
//   ./render_demo 512 sparse
//   ./render_demo 512 clustered optimized
//
// Output files are render_<scene>_reference.ppm and render_<scene>_<variant>.ppm
// in the current directory. The single run timings are only a diagnostic, use
// ./render_bench for the measurements that go into the report.
#include "renderer.h"
#include "scenes.h"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
int main(int argc,char** argv) {
    int size=argc>1?std::atoi(argv[1]):256;
    std::string scene=argc>2?argv[2]:"dense";
    std::string variant=argc>3?argv[3]:"parallel";
    if(size<=0||size>4096) {std::cerr<<"size must be 1..4096\n";return 2;}
    std::vector<Circle> circles;
    if(!make_scene(scene,circles)) {
        std::cerr<<"unknown scene '"<<scene<<"', choose from:";
        for(const std::string& name:scene_names()) std::cerr<<" "<<name;
        std::cerr<<"\n";
        return 2;
    }
    if(variant!="parallel"&&variant!="optimized") {
        std::cerr<<"variant must be parallel or optimized\n";
        return 2;
    }
    Image (*render)(int,int,const std::vector<Circle>&)=
        variant=="optimized"?render_optimized:render_parallel;
    auto t0=std::chrono::steady_clock::now();
    Image ref=render_reference(size,size,circles);
    auto t1=std::chrono::steady_clock::now();
    Image out=render(size,size,circles);
    auto t2=std::chrono::steady_clock::now();
    save_ppm(ref,("render_"+scene+"_reference.ppm").c_str());
    save_ppm(out,("render_"+scene+"_"+variant+".ppm").c_str());
    bool ok=images_close(ref,out);
    std::cout<<"RENDER "<<size<<"x"<<size<<" scene="<<scene<<" variant="<<variant
             <<" circles="<<circles.size()<<" serial_ms="
             <<std::chrono::duration<double,std::milli>(t1-t0).count()
             <<" parallel_ms="<<std::chrono::duration<double,std::milli>(t2-t1).count()
             <<" correctness="<<(ok?"PASS":"FAIL (complete TODO)")<<"\n";
    return ok?0:1;
}
