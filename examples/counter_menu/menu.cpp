#define FTGD_IMPLEMENTATION
#define FTGD_LOWERCASE_GLYPHS
#include "../../ftgd.hpp"
#include <iostream>

// Line protocol on stdin. User input never becomes a command or a filename.
int main(int argc, char** argv) {
    if (argc != 4) return 2;
    ftgd::Config cfg;
    cfg.title = "KIKO COUNTER / GIF MENU";
    cfg.base_url = argv[1];
    cfg.app_name = std::string("count/gifmenu/") + argv[2];
    cfg.page = argv[3];
    cfg.width = 1200;
    cfg.show_help = false; // Render every control below, not the default three.
    std::vector<std::pair<std::string, std::string>> lines;
    std::string line;
    while (std::getline(std::cin, line)) {
        auto tab = line.find('\t');
        if (tab != std::string::npos)
            lines.emplace_back(line.substr(0, tab), line.substr(tab + 1));
    }
    cfg.height = 130 + static_cast<int>(lines.size()) * 33;
    for (const auto& item : lines) if (item.first == "I") cfg.height += 580;
    ftgd::Dashboard dash(cfg);
    dash.begin();
    for (const auto& item : lines) {
        if (item.first == "I") dash.image(ftgd::load_ppm(item.second.c_str()), 960, 576);
        else if (item.first == "H") dash.heading(item.second.c_str());
        else dash.text(item.second.c_str());
    }
    dash.end();
    auto bytes = dash.gif();
    std::cout.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    return std::cout ? 0 : 1;
}
