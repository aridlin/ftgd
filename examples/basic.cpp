#define FTGD_IMPLEMENTATION
#include "../ftgd.hpp"

#include <cstdio>

static ftgd::Image showcase_image() {
    ftgd::Image img;
    img.width = 360;
    img.height = 126;
    img.pixels.resize(static_cast<size_t>(img.width * img.height));
    for (int y = 0; y < img.height; ++y) {
        for (int x = 0; x < img.width; ++x) {
            uint8_t r = static_cast<uint8_t>(32 + x * 150 / img.width);
            uint8_t g = static_cast<uint8_t>(90 + y * 110 / img.height);
            uint8_t b = static_cast<uint8_t>(220 - x * 70 / img.width);
            if (((x / 18) + (y / 18)) % 2 == 0) {
                r = static_cast<uint8_t>(r + 22);
                g = static_cast<uint8_t>(g + 18);
            }
            img.pixels[static_cast<size_t>(y * img.width + x)] = ftgd::color(r, g, b);
        }
    }
    return img;
}

int main() {
    ftgd::Config cfg;
    cfg.title = "FTGD SINGLE HEADER GIF DASHBOARD";
    cfg.width = 1200;
    cfg.height = 675;
    cfg.base_url = "https://website.com";
    cfg.app_name = "appname";
    cfg.page = "p";
    cfg.animated = true;
    cfg.frame_delay_cs = 28;
    cfg.style.background = ftgd::color(244, 248, 252);
    cfg.style.panel = ftgd::color(255, 255, 255);
    cfg.style.panel_alt = ftgd::color(226, 237, 249);
    cfg.style.border = ftgd::color(57, 90, 128);
    cfg.style.text = ftgd::color(12, 23, 38);
    cfg.style.text_dim = ftgd::color(55, 72, 95);
    cfg.style.accent = ftgd::color(0, 113, 227);
    cfg.style.success = ftgd::color(15, 150, 92);
    cfg.style.warning = ftgd::color(218, 128, 16);
    cfg.style.danger = ftgd::color(205, 50, 68);

    ftgd::create_dashboard(cfg);
    ftgd::begin("p");
    ftgd::stat("HEADER", "ONLY", ftgd::color(15, 150, 92));
    ftgd::stat("OUTPUT", "GIF89A", ftgd::color(0, 113, 227));
    ftgd::stat("CONTROL", "S/X/Y", ftgd::color(218, 128, 16));
    ftgd::heading("FUCK THIS GIF DASHBOARD");
    ftgd::text("Immediate mode widgets render to a GIF response for Discord embeds.");
    ftgd::progress("LIVE RENDER + COMMAND MAP", 0.86f, ftgd::color(0, 113, 227));
    ftgd::separator();
    ftgd::text("URL: WEBSITE.COM/APPNAME/P.GIF");
    ftgd::text("SEND: S/P/1P  ->  WEBSITE.COM/APPNAME/1P.GIF");
    ftgd::image(showcase_image(), 360, 126);
    ftgd::link("OPEN NEXT DASHBOARD PAGE", "1p", "turn p.gif into 1p.gif");
    ftgd::command("RETURN HOME", "1p", "p", "turn 1p.gif back into p.gif");
    ftgd::command("DEEP LINK", "p", "stats/cpu", "jump to nested dashboard pages");
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
