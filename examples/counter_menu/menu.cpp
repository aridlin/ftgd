#define FTGD_IMPLEMENTATION
#include "../../ftgd.hpp"
#include <iostream>

// TrueType typography and layout are rasterized by Pillow. FTGD remains the
// GIF encoder; its tiny built-in bitmap font is not used for these menus.
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    auto image = ftgd::load_ppm(argv[1]);
    if (!image.valid()) return 3;
    ftgd::detail::Canvas canvas;
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.pixels = std::move(image.pixels);
    auto bytes = ftgd::detail::encode_gif({canvas}, 35);
    std::cout.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    return std::cout ? 0 : 1;
}
