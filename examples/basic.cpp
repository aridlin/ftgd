#define FTGD_IMPLEMENTATION
#include "../ftgd.hpp"

#include <cstdio>
#include <string>

static bool write_file(const char* path, const std::vector<uint8_t>& bytes) {
    FILE* f = std::fopen(path, "wb");
    if (!f) return false;
    std::fwrite(bytes.data(), 1, bytes.size(), f);
    std::fclose(f);
    return true;
}

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

static void add_common_commands(const char* page) {
    std::string current = page ? page : "p";
    ftgd::command("GO FORWARD", current.c_str(), "1p", "change this page into 1p.gif");
    ftgd::command("GO BACK A LEVEL", current.c_str(), "bp", "change this page into bp.gif");
    ftgd::command("OPEN CPU PANEL", current.c_str(), "cp", "change this page into cp.gif");
}

static std::vector<uint8_t> render_page(const char* page, const char* title, const char* primary, float progress, ftgd::Color accent) {
    ftgd::begin(page);
    ftgd::stat("PAGE", page, accent);
    ftgd::stat("OUTPUT", "GIF89A", ftgd::color(0, 113, 227));
    ftgd::stat("CONTROL", "S/X/Y", ftgd::color(218, 128, 16));
    ftgd::heading(title);
    ftgd::text(primary);
    ftgd::progress("LIVE RENDER + COMMAND MAP", progress, accent);
    ftgd::separator();
    std::string url = "URL: WEBSITE.COM/APPNAME/";
    url += page;
    url += ".GIF";
    ftgd::text(url.c_str());
    ftgd::text("SEND: S/P/1P OR S/P/BP OR S/P/CP TO STEER THE EMBED URL");
    ftgd::image(showcase_image(), 360, 126);
    add_common_commands(page);
    ftgd::end();
    return ftgd::gif();
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
    std::vector<uint8_t> home = render_page("p", "FUCK THIS GIF DASHBOARD", "Immediate mode widgets render to a GIF response for Discord embeds.", 0.86f, ftgd::color(15, 150, 92));
    std::vector<uint8_t> forward = render_page("1p", "FORWARD PAGE 1P", "This is the next dashboard reached by sending s/p/1p in Discord.", 0.64f, ftgd::color(0, 113, 227));
    std::vector<uint8_t> back = render_page("bp", "BACK PAGE BP", "This is the back-level dashboard reached by sending s/p/bp.", 0.36f, ftgd::color(218, 128, 16));
    std::vector<uint8_t> cpu = render_page("cp", "CPU PANEL CP", "This page proves command targets are real GIF files, not dead links.", 0.78f, ftgd::color(205, 50, 68));
    if (!write_file("build/p.gif", home)) return 1;
    if (!write_file("build/1p.gif", forward)) return 1;
    if (!write_file("build/bp.gif", back)) return 1;
    if (!write_file("build/cp.gif", cpu)) return 1;
    write_file("build/basic.gif", home);

    std::printf("url: %s\n", ftgd::url_for("p").c_str());
    std::printf("command: %s\n", ftgd::command_s("p", "1p").c_str());
    std::printf("back command: %s\n", ftgd::command_s("p", "bp").c_str());
    std::printf("cpu command: %s\n", ftgd::command_s("p", "cp").c_str());
    std::printf("next page: %s\n", ftgd::apply_command("p", "s/p/1p").c_str());
    std::printf("gif bytes: %zu\n", home.size());
    ftgd::shutdown();
    return 0;
}
