#define FTGD_IMPLEMENTATION
#include "../ftgd.hpp"

#include <cstdio>

int main() {
    ftgd::Config cfg;
    cfg.title = "FTGD STATUS";
    cfg.base_url = "https://website.com";
    cfg.app_name = "appname";
    cfg.page = "p";
    cfg.animated = true;

    ftgd::create_dashboard(cfg);
    ftgd::begin("p");
    ftgd::stat("USERS", "128", ftgd::color(72, 190, 130));
    ftgd::stat("QUEUE", "04", ftgd::color(245, 173, 85));
    ftgd::stat("PAGE", "p", ftgd::color(72, 177, 255));
    ftgd::heading("FUCK THIS GIF DASHBOARD");
    ftgd::text("A dashboard that returns a GIF embed and is steered by Discord s/x/y commands.");
    ftgd::progress("RENDER PIPELINE", 0.72f);
    ftgd::image(ftgd::checker_image(220, 92, ftgd::color(72, 177, 255), ftgd::color(22, 27, 34), 16), 220, 92);
    ftgd::link("OPEN PAGE 1p", "1p", "changes website.com/appname/p.gif to /1p.gif");
    ftgd::command("BACK TO p", "1p", "p", "returns to the root panel");
    ftgd::end();

    std::vector<uint8_t> bytes = ftgd::gif();
    FILE* f = std::fopen("build/basic.gif", "wb");
    if (!f) return 1;
    std::fwrite(bytes.data(), 1, bytes.size(), f);
    std::fclose(f);

    std::printf("url: %s\n", ftgd::url().c_str());
    std::printf("command: %s\n", ftgd::command_s("p", "1p").c_str());
    std::printf("next page: %s\n", ftgd::apply_command("p", "s/p/1p").c_str());
    std::printf("gif bytes: %zu\n", bytes.size());
    ftgd::shutdown();
    return 0;
}
