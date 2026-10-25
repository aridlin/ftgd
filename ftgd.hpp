// ftgd.hpp - Fuck This GIF Dashboard
//
// Usage:
//   #define FTGD_IMPLEMENTATION
//   #include "ftgd.hpp"
//
// ftgd is a single-header C++17 dashboard renderer for Discord-embeddable GIFs.
// The API follows the immediate-mode shape of the FT family while returning a
// GIF byte buffer instead of opening a native, TUI, or HTTP window.

#pragma once

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <initializer_list>
#include <map>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#ifndef FTGD_VERSION_MAJOR
#define FTGD_VERSION_MAJOR 0
#endif
#ifndef FTGD_VERSION_MINOR
#define FTGD_VERSION_MINOR 2
#endif
#ifndef FTGD_VERSION_PATCH
#define FTGD_VERSION_PATCH 0
#endif

namespace ftgd {

struct Color {
    uint8_t r = 0;
    uint8_t g = 0;
    uint8_t b = 0;
    uint8_t a = 255;
};

struct Style {
    Color background = {13, 17, 23, 255};
    Color panel = {22, 27, 34, 255};
    Color panel_alt = {32, 39, 50, 255};
    Color border = {54, 63, 78, 255};
    Color text = {236, 241, 247, 255};
    Color text_dim = {148, 163, 184, 255};
    Color accent = {72, 177, 255, 255};
    Color success = {72, 190, 130, 255};
    Color warning = {245, 173, 85, 255};
    Color danger = {238, 96, 96, 255};
    int radius = 8;
    int margin = 24;
    int gap = 12;
    int font_scale = 2;
};

struct Config {
    const char* title = "FTGD Dashboard";
    int width = 960;
    int height = 540;
    std::string base_url = "https://website.com";
    std::string app_name = "appname";
    std::string page = "p";
    std::string page_suffix = ".gif";
    bool show_help = true;
    bool animated = false;
    int frame_delay_cs = 35;
    Style style = {};
};

struct Image {
    int width = 0;
    int height = 0;
    std::vector<Color> pixels;

    bool valid() const { return width > 0 && height > 0 && pixels.size() == static_cast<size_t>(width * height); }
};

struct Command {
    std::string label;
    std::string syntax;
    std::string result_page;
    std::string help;
};

struct Response {
    std::string content_type = "image/gif";
    std::vector<uint8_t> body;
};

enum class WidgetKind {
    Text,
    Stat,
    Progress,
    Image,
    Separator,
};

struct Widget {
    WidgetKind kind = WidgetKind::Text;
    std::string a;
    std::string b;
    float value = 0.0f;
    Image image;
    int image_width = 0;
    int image_height = 0;
    Color color = {0, 0, 0, 0};
};

class Dashboard {
public:
    explicit Dashboard(const Config& config = {});

    void begin(const char* page = nullptr);
    void end();

    void text(const char* value);
    void heading(const char* value);
    void stat(const char* label, const char* value, Color accent = {});
    void progress(const char* label, float value, Color accent = {});
    void separator();
    void image(const Image& value, int width = 0, int height = 0);

    void command(const char* label, const char* from, const char* to, const char* help = nullptr);
    void link(const char* label, const char* to, const char* help = nullptr);

    const Config& config() const { return cfg_; }
    const std::string& page() const { return page_; }
    const std::vector<Widget>& widgets() const { return widgets_; }
    const std::vector<Command>& commands() const { return commands_; }

    std::string url() const;
    std::string url_for(const std::string& page) const;
    std::vector<uint8_t> gif() const;
    Response response() const;

private:
    Config cfg_;
    std::string page_;
    std::vector<Widget> widgets_;
    std::vector<Command> commands_;
};

Style default_dark_style();
Style ghostty_green_style();
Color color(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255);
Color color_from_hex(const char* hex);

bool create_dashboard(const Config& cfg = {});
void shutdown();
void begin(const char* page = nullptr);
void end();
Dashboard& current();

void text(const char* value);
void heading(const char* value);
void stat(const char* label, const char* value, Color accent = {});
void progress(const char* label, float value, Color accent = {});
void separator();
void image(const Image& value, int width = 0, int height = 0);
void command(const char* label, const char* from, const char* to, const char* help = nullptr);
void link(const char* label, const char* to, const char* help = nullptr);

std::string url();
std::string url_for(const std::string& page);
std::vector<uint8_t> gif();
Response response();

std::string command_s(const std::string& from, const std::string& to);
std::string apply_command(const std::string& page, const std::string& command);
std::string apply_commands(std::string page, std::initializer_list<std::string> commands);
std::string page_from_url(const std::string& url_value, const Config& cfg = {});
// Encode an externally rasterized image (e.g. TrueType text) without bitmap widgets.
std::vector<uint8_t> encode_image(const Image& image);
// Insert a choice before the first marker, retaining it for the next edit.
std::string append_command(const std::string& choice, const std::string& marker = "b");
Image load_ppm(const char* path);
Image image_from_rgba(int width, int height, const uint8_t* rgba);
Image checker_image(int width, int height, Color a, Color b, int cell = 12);

namespace detail {

struct Canvas {
    int width = 0;
    int height = 0;
    std::vector<Color> pixels;
};

Canvas make_canvas(int width, int height, Color fill);
void fill_rect(Canvas& c, int x, int y, int w, int h, Color color);
void stroke_rect(Canvas& c, int x, int y, int w, int h, Color color);
void draw_text(Canvas& c, int x, int y, const std::string& text, Color color, int scale = 2);
int text_width(const std::string& text, int scale = 2);
void blit_image(Canvas& c, const Image& img, int x, int y, int w, int h);
std::vector<uint8_t> encode_gif(const std::vector<Canvas>& frames, int delay_cs);
Canvas render_dashboard(const Dashboard& dash, int frame_index);

} // namespace detail

} // namespace ftgd

#ifdef FTGD_IMPLEMENTATION

namespace ftgd {

Dashboard::Dashboard(const Config& config) : cfg_(config), page_(config.page) {}

void Dashboard::begin(const char* page) {
    if (page) page_ = page;
    widgets_.clear();
    commands_.clear();
}

void Dashboard::end() {}

void Dashboard::text(const char* value) {
    Widget w;
    w.kind = WidgetKind::Text;
    w.a = value ? value : "";
    widgets_.push_back(w);
}

void Dashboard::heading(const char* value) {
    Widget w;
    w.kind = WidgetKind::Text;
    w.a = value ? value : "";
    w.value = 1.0f;
    widgets_.push_back(w);
}

void Dashboard::stat(const char* label, const char* value, Color accent) {
    Widget w;
    w.kind = WidgetKind::Stat;
    w.a = label ? label : "";
    w.b = value ? value : "";
    w.color = accent.a ? accent : cfg_.style.accent;
    widgets_.push_back(w);
}

void Dashboard::progress(const char* label, float value, Color accent) {
    Widget w;
    w.kind = WidgetKind::Progress;
    w.a = label ? label : "";
    w.value = std::max(0.0f, std::min(1.0f, value));
    w.color = accent.a ? accent : cfg_.style.accent;
    widgets_.push_back(w);
}

void Dashboard::separator() {
    Widget w;
    w.kind = WidgetKind::Separator;
    widgets_.push_back(w);
}

void Dashboard::image(const Image& value, int width, int height) {
    Widget w;
    w.kind = WidgetKind::Image;
    w.image = value;
    w.image_width = width;
    w.image_height = height;
    widgets_.push_back(w);
}

void Dashboard::command(const char* label, const char* from, const char* to, const char* help) {
    Command c;
    c.label = label ? label : "";
    c.syntax = command_s(from ? from : "", to ? to : "");
    c.result_page = to ? to : "";
    c.help = help ? help : "";
    commands_.push_back(c);
}

void Dashboard::link(const char* label, const char* to, const char* help) {
    command(label, page_.c_str(), to, help);
}

static std::string trim_slashes(std::string s) {
    while (!s.empty() && s.front() == '/') s.erase(s.begin());
    while (!s.empty() && s.back() == '/') s.pop_back();
    return s;
}

std::string Dashboard::url_for(const std::string& page) const {
    std::string base = cfg_.base_url;
    while (!base.empty() && base.back() == '/') base.pop_back();
    std::string app = trim_slashes(cfg_.app_name);
    std::string p = trim_slashes(page);
    std::string out = base;
    if (!app.empty()) out += "/" + app;
    if (!p.empty()) out += "/" + p + cfg_.page_suffix;
    return out;
}

std::string Dashboard::url() const {
    return url_for(page_);
}

std::vector<uint8_t> Dashboard::gif() const {
    std::vector<detail::Canvas> frames;
    frames.push_back(detail::render_dashboard(*this, 0));
    if (cfg_.animated) frames.push_back(detail::render_dashboard(*this, 1));
    return detail::encode_gif(frames, cfg_.frame_delay_cs);
}

Response Dashboard::response() const {
    Response r;
    r.body = gif();
    return r;
}

Style default_dark_style() { return Style{}; }

Style ghostty_green_style() {
    Style s;
    s.background = {9, 12, 11, 255};
    s.panel = {15, 23, 20, 255};
    s.panel_alt = {22, 34, 29, 255};
    s.border = {39, 72, 58, 255};
    s.text = {231, 247, 238, 255};
    s.text_dim = {141, 176, 158, 255};
    s.accent = {72, 224, 148, 255};
    return s;
}

Color color(uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    return {r, g, b, a};
}

Color color_from_hex(const char* hex) {
    if (!hex) return {};
    std::string s = hex;
    if (!s.empty() && s[0] == '#') s.erase(s.begin());
    if (s.size() != 6 && s.size() != 8) return {};
    unsigned int value = 0;
    std::stringstream ss;
    ss << std::hex << s;
    ss >> value;
    if (s.size() == 6) return {static_cast<uint8_t>((value >> 16) & 255), static_cast<uint8_t>((value >> 8) & 255), static_cast<uint8_t>(value & 255), 255};
    return {static_cast<uint8_t>((value >> 24) & 255), static_cast<uint8_t>((value >> 16) & 255), static_cast<uint8_t>((value >> 8) & 255), static_cast<uint8_t>(value & 255)};
}

static Dashboard*& current_ptr() {
    static Dashboard* dash = nullptr;
    return dash;
}

bool create_dashboard(const Config& cfg) {
    shutdown();
    current_ptr() = new Dashboard(cfg);
    return true;
}

void shutdown() {
    delete current_ptr();
    current_ptr() = nullptr;
}

Dashboard& current() {
    if (!current_ptr()) create_dashboard();
    return *current_ptr();
}

void begin(const char* page) { current().begin(page); }
void end() { current().end(); }
void text(const char* value) { current().text(value); }
void heading(const char* value) { current().heading(value); }
void stat(const char* label, const char* value, Color accent) { current().stat(label, value, accent); }
void progress(const char* label, float value, Color accent) { current().progress(label, value, accent); }
void separator() { current().separator(); }
void image(const Image& value, int width, int height) { current().image(value, width, height); }
void command(const char* label, const char* from, const char* to, const char* help) { current().command(label, from, to, help); }
void link(const char* label, const char* to, const char* help) { current().link(label, to, help); }
std::string url() { return current().url(); }
std::string url_for(const std::string& page) { return current().url_for(page); }
std::vector<uint8_t> gif() { return current().gif(); }
Response response() { return current().response(); }

std::string command_s(const std::string& from, const std::string& to) {
    return "s/" + from + "/" + to;
}

std::string apply_command(const std::string& page, const std::string& command) {
    if (command.size() < 4 || command[0] != 's') return page;
    char delim = command[1];
    size_t mid = command.find(delim, 2);
    if (mid == std::string::npos) return page;
    std::string from = command.substr(2, mid - 2);
    std::string to = command.substr(mid + 1);
    if (from.empty()) return page;
    std::string out = page;
    size_t pos = out.find(from);
    if (pos != std::string::npos) out.replace(pos, from.size(), to);
    return out;
}

std::string apply_commands(std::string page, std::initializer_list<std::string> commands) {
    for (const std::string& c : commands) page = apply_command(page, c);
    return page;
}

std::string page_from_url(const std::string& url_value, const Config& cfg) {
    std::string base = cfg.base_url;
    while (!base.empty() && base.back() == '/') base.pop_back();
    std::string prefix = base;
    std::string app = trim_slashes(cfg.app_name);
    if (!app.empty()) prefix += "/" + app;
    prefix += "/";
    if (url_value.rfind(prefix, 0) != 0) return {};
    std::string page = url_value.substr(prefix.size());
    if (page.size() >= cfg.page_suffix.size() && page.substr(page.size() - cfg.page_suffix.size()) == cfg.page_suffix) {
        page.resize(page.size() - cfg.page_suffix.size());
    }
    return page;
}

static bool ppm_read_token(std::istream& in, std::string& token) {
    token.clear();
    char ch = 0;
    while (in.get(ch)) {
        if (ch == '#') {
            std::string discard;
            std::getline(in, discard);
            continue;
        }
        if (!std::isspace(static_cast<unsigned char>(ch))) {
            token.push_back(ch);
            break;
        }
    }
    while (in.get(ch)) {
        if (std::isspace(static_cast<unsigned char>(ch))) break;
        token.push_back(ch);
    }
    return !token.empty();
}

Image load_ppm(const char* path) {
    Image img;
    if (!path) return img;
    std::ifstream in(path, std::ios::binary);
    if (!in) return img;
    std::string magic, tok;
    if (!ppm_read_token(in, magic)) return img;
    if (magic != "P6" && magic != "P3") return img;
    if (!ppm_read_token(in, tok)) return img;
    img.width = std::atoi(tok.c_str());
    if (!ppm_read_token(in, tok)) return img;
    img.height = std::atoi(tok.c_str());
    if (!ppm_read_token(in, tok)) return img;
    int maxv = std::max(1, std::atoi(tok.c_str()));
    if (img.width <= 0 || img.height <= 0) return {};
    img.pixels.resize(static_cast<size_t>(img.width * img.height));
    if (magic == "P6") {
        for (int i = 0; i < img.width * img.height; ++i) {
            unsigned char rgb[3] = {0, 0, 0};
            in.read(reinterpret_cast<char*>(rgb), 3);
            img.pixels[static_cast<size_t>(i)] = {static_cast<uint8_t>(rgb[0] * 255 / maxv), static_cast<uint8_t>(rgb[1] * 255 / maxv), static_cast<uint8_t>(rgb[2] * 255 / maxv), 255};
        }
    } else {
        for (int i = 0; i < img.width * img.height; ++i) {
            std::string r, g, b;
            if (!ppm_read_token(in, r) || !ppm_read_token(in, g) || !ppm_read_token(in, b)) return {};
            img.pixels[static_cast<size_t>(i)] = {static_cast<uint8_t>(std::atoi(r.c_str()) * 255 / maxv), static_cast<uint8_t>(std::atoi(g.c_str()) * 255 / maxv), static_cast<uint8_t>(std::atoi(b.c_str()) * 255 / maxv), 255};
        }
    }
    return img;
}

Image image_from_rgba(int width, int height, const uint8_t* rgba) {
    Image img;
    if (width <= 0 || height <= 0 || !rgba) return img;
    img.width = width;
    img.height = height;
    img.pixels.resize(static_cast<size_t>(width * height));
    for (int i = 0; i < width * height; ++i) {
        img.pixels[static_cast<size_t>(i)] = {rgba[i * 4 + 0], rgba[i * 4 + 1], rgba[i * 4 + 2], rgba[i * 4 + 3]};
    }
    return img;
}

Image checker_image(int width, int height, Color a, Color b, int cell) {
    Image img;
    if (width <= 0 || height <= 0) return img;
    img.width = width;
    img.height = height;
    img.pixels.resize(static_cast<size_t>(width * height));
    cell = std::max(1, cell);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            img.pixels[static_cast<size_t>(y * width + x)] = (((x / cell) + (y / cell)) & 1) ? b : a;
        }
    }
    return img;
}

std::vector<uint8_t> encode_image(const Image& image) {
    if (!image.valid()) return {};
    detail::Canvas canvas;
    canvas.width = image.width;
    canvas.height = image.height;
    canvas.pixels = image.pixels;
    return detail::encode_gif({canvas}, 35);
}

std::string append_command(const std::string& choice, const std::string& marker) {
    if (marker.empty() || choice.find(marker) != std::string::npos ||
        marker.find('/') != std::string::npos || choice.find('/') != std::string::npos)
        return {};
    return command_s(marker, choice + marker);
}

namespace detail {

Canvas make_canvas(int width, int height, Color fill) {
    Canvas c;
    c.width = std::max(1, width);
    c.height = std::max(1, height);
    c.pixels.assign(static_cast<size_t>(c.width * c.height), fill);
    return c;
}

static void put_pixel(Canvas& c, int x, int y, Color color) {
    if (x < 0 || y < 0 || x >= c.width || y >= c.height) return;
    if (color.a == 255) {
        c.pixels[static_cast<size_t>(y * c.width + x)] = color;
        return;
    }
    Color& dst = c.pixels[static_cast<size_t>(y * c.width + x)];
    float a = color.a / 255.0f;
    dst.r = static_cast<uint8_t>(dst.r * (1.0f - a) + color.r * a);
    dst.g = static_cast<uint8_t>(dst.g * (1.0f - a) + color.g * a);
    dst.b = static_cast<uint8_t>(dst.b * (1.0f - a) + color.b * a);
}

void fill_rect(Canvas& c, int x, int y, int w, int h, Color color) {
    for (int yy = std::max(0, y); yy < std::min(c.height, y + h); ++yy) {
        for (int xx = std::max(0, x); xx < std::min(c.width, x + w); ++xx) put_pixel(c, xx, yy, color);
    }
}

void stroke_rect(Canvas& c, int x, int y, int w, int h, Color color) {
    fill_rect(c, x, y, w, 1, color);
    fill_rect(c, x, y + h - 1, w, 1, color);
    fill_rect(c, x, y, 1, h, color);
    fill_rect(c, x + w - 1, y, 1, h, color);
}

static std::array<uint8_t, 7> glyph(char ch) {
#ifdef FTGD_LOWERCASE_GLYPHS
    // Opt in when text contains case-sensitive URLs or Discord commands.
    static const std::array<std::array<uint8_t, 7>, 26> lower = {{
        {0,0,14,1,15,17,15}, {16,16,30,17,17,17,30},
        {0,0,14,16,16,17,14}, {1,1,15,17,17,17,15},
        {0,0,14,17,31,16,14}, {6,9,8,28,8,8,8},
        {0,15,17,17,15,1,14}, {16,16,30,17,17,17,17},
        {4,0,12,4,4,4,14}, {2,0,6,2,2,18,12},
        {16,16,18,20,24,20,18}, {12,4,4,4,4,4,14},
        {0,0,26,21,21,21,21}, {0,0,30,17,17,17,17},
        {0,0,14,17,17,17,14}, {0,30,17,17,30,16,16},
        {0,15,17,17,15,1,1}, {0,0,22,25,16,16,16},
        {0,0,15,16,14,1,30}, {8,8,28,8,8,9,6},
        {0,0,17,17,17,19,13}, {0,0,17,17,17,10,4},
        {0,0,17,17,21,21,10}, {0,0,17,10,4,10,17},
        {0,17,17,17,15,1,14}, {0,0,31,2,4,8,31}
    }};
    if (ch >= 'a' && ch <= 'z') return lower[static_cast<size_t>(ch - 'a')];
#endif
    ch = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
    switch (ch) {
    case 'A': return {14, 17, 17, 31, 17, 17, 17};
    case 'B': return {30, 17, 17, 30, 17, 17, 30};
    case 'C': return {14, 17, 16, 16, 16, 17, 14};
    case 'D': return {30, 17, 17, 17, 17, 17, 30};
    case 'E': return {31, 16, 16, 30, 16, 16, 31};
    case 'F': return {31, 16, 16, 30, 16, 16, 16};
    case 'G': return {14, 17, 16, 23, 17, 17, 15};
    case 'H': return {17, 17, 17, 31, 17, 17, 17};
    case 'I': return {14, 4, 4, 4, 4, 4, 14};
    case 'J': return {1, 1, 1, 1, 17, 17, 14};
    case 'K': return {17, 18, 20, 24, 20, 18, 17};
    case 'L': return {16, 16, 16, 16, 16, 16, 31};
    case 'M': return {17, 27, 21, 21, 17, 17, 17};
    case 'N': return {17, 25, 21, 19, 17, 17, 17};
    case 'O': return {14, 17, 17, 17, 17, 17, 14};
    case 'P': return {30, 17, 17, 30, 16, 16, 16};
    case 'Q': return {14, 17, 17, 17, 21, 18, 13};
    case 'R': return {30, 17, 17, 30, 20, 18, 17};
    case 'S': return {15, 16, 16, 14, 1, 1, 30};
    case 'T': return {31, 4, 4, 4, 4, 4, 4};
    case 'U': return {17, 17, 17, 17, 17, 17, 14};
    case 'V': return {17, 17, 17, 17, 17, 10, 4};
    case 'W': return {17, 17, 17, 21, 21, 27, 17};
    case 'X': return {17, 17, 10, 4, 10, 17, 17};
    case 'Y': return {17, 17, 10, 4, 4, 4, 4};
    case 'Z': return {31, 1, 2, 4, 8, 16, 31};
    case '0': return {14, 17, 19, 21, 25, 17, 14};
    case '1': return {4, 12, 4, 4, 4, 4, 14};
    case '2': return {14, 17, 1, 2, 4, 8, 31};
    case '3': return {30, 1, 1, 14, 1, 1, 30};
    case '4': return {2, 6, 10, 18, 31, 2, 2};
    case '5': return {31, 16, 16, 30, 1, 1, 30};
    case '6': return {14, 16, 16, 30, 17, 17, 14};
    case '7': return {31, 1, 2, 4, 8, 8, 8};
    case '8': return {14, 17, 17, 14, 17, 17, 14};
    case '9': return {14, 17, 17, 15, 1, 1, 14};
    case '/': return {1, 1, 2, 4, 8, 16, 16};
    case '.': return {0, 0, 0, 0, 0, 12, 12};
    case ':': return {0, 12, 12, 0, 12, 12, 0};
    case '-': return {0, 0, 0, 31, 0, 0, 0};
    case '_': return {0, 0, 0, 0, 0, 0, 31};
    case '+': return {0, 4, 4, 31, 4, 4, 0};
    case '%': return {17, 2, 4, 8, 16, 17, 0};
    case '#': return {10, 31, 10, 10, 31, 10, 0};
    case '=': return {0, 31, 0, 31, 0, 0, 0};
    case '>': return {16, 8, 4, 2, 4, 8, 16};
    case '<': return {1, 2, 4, 8, 4, 2, 1};
    case '[': return {14, 8, 8, 8, 8, 8, 14};
    case ']': return {14, 2, 2, 2, 2, 2, 14};
    case ' ': return {0, 0, 0, 0, 0, 0, 0};
    case '~': return {0,0,9,22,0,0,0};
    case '|': return {4,4,4,4,4,4,4};
    case '!': return {4,4,4,4,4,0,4};
    case '(': return {2,4,8,8,8,4,2};
    case ')': return {8,4,2,2,2,4,8};
    case ',': return {0,0,0,0,4,4,8};
    case ';': return {0,4,4,0,4,4,8};
    case '*': return {0,21,14,31,14,21,0};
    case '\'': return {4,4,8,0,0,0,0};
    default: return {14, 17, 1, 2, 4, 0, 4};
    }
}

int text_width(const std::string& text, int scale) {
    return static_cast<int>(text.size()) * 6 * scale;
}

void draw_text(Canvas& c, int x, int y, const std::string& text, Color color, int scale) {
    int cursor = x;
    for (char ch : text) {
        auto g = glyph(ch);
        for (int row = 0; row < 7; ++row) {
            for (int col = 0; col < 5; ++col) {
                if (g[static_cast<size_t>(row)] & (1 << (4 - col))) {
                    fill_rect(c, cursor + col * scale, y + row * scale, scale, scale, color);
                }
            }
        }
        cursor += 6 * scale;
    }
}

void blit_image(Canvas& c, const Image& img, int x, int y, int w, int h) {
    if (!img.valid() || w <= 0 || h <= 0) return;
    for (int yy = 0; yy < h; ++yy) {
        int sy = yy * img.height / h;
        for (int xx = 0; xx < w; ++xx) {
            int sx = xx * img.width / w;
            put_pixel(c, x + xx, y + yy, img.pixels[static_cast<size_t>(sy * img.width + sx)]);
        }
    }
}

static std::vector<Color> palette() {
    std::vector<Color> p;
    int levels[6] = {0, 51, 102, 153, 204, 255};
    for (int r : levels) for (int g : levels) for (int b : levels) p.push_back({static_cast<uint8_t>(r), static_cast<uint8_t>(g), static_cast<uint8_t>(b), 255});
    for (int i = 0; i < 24; ++i) {
        uint8_t v = static_cast<uint8_t>(i * 255 / 23);
        p.push_back({v, v, v, 255});
    }
    std::vector<Color> extras = {
        {13,17,23,255},{22,27,34,255},{32,39,50,255},{54,63,78,255},
        {236,241,247,255},{148,163,184,255},{72,177,255,255},{72,190,130,255},
        {245,173,85,255},{238,96,96,255},{9,12,11,255},{15,23,20,255},
        {22,34,29,255},{39,72,58,255},{231,247,238,255},{72,224,148,255}
    };
    for (Color c : extras) p.push_back(c);
    while (p.size() < 256) p.push_back({0, 0, 0, 255});
    p.resize(256);
    return p;
}

static uint8_t nearest_palette(Color c, const std::vector<Color>& p, std::unordered_map<uint32_t, uint8_t>& cache) {
    uint32_t key = (static_cast<uint32_t>(c.r) << 16) | (static_cast<uint32_t>(c.g) << 8) | c.b;
    auto it = cache.find(key);
    if (it != cache.end()) return it->second;
    int best = 0;
    int best_dist = 1 << 30;
    for (int i = 0; i < 256; ++i) {
        int dr = static_cast<int>(c.r) - p[static_cast<size_t>(i)].r;
        int dg = static_cast<int>(c.g) - p[static_cast<size_t>(i)].g;
        int db = static_cast<int>(c.b) - p[static_cast<size_t>(i)].b;
        int dist = dr * dr + dg * dg + db * db;
        if (dist < best_dist) {
            best_dist = dist;
            best = i;
        }
    }
    cache[key] = static_cast<uint8_t>(best);
    return static_cast<uint8_t>(best);
}

static void push_u16(std::vector<uint8_t>& out, int v) {
    out.push_back(static_cast<uint8_t>(v & 255));
    out.push_back(static_cast<uint8_t>((v >> 8) & 255));
}

struct BitWriter {
    std::vector<uint8_t> bytes;
    uint32_t acc = 0;
    int bits = 0;
    void code(int value, int size) {
        acc |= static_cast<uint32_t>(value) << bits;
        bits += size;
        while (bits >= 8) {
            bytes.push_back(static_cast<uint8_t>(acc & 255));
            acc >>= 8;
            bits -= 8;
        }
    }
    void finish() {
        if (bits > 0) bytes.push_back(static_cast<uint8_t>(acc & 255));
        acc = 0;
        bits = 0;
    }
};

static std::vector<uint8_t> lzw(const std::vector<uint8_t>& indices) {
    constexpr int clear = 256, eoi = 257;
    BitWriter bw;
    std::unordered_map<uint32_t, int> dictionary;
    dictionary.reserve(4096);
    int next = 258, decoder_next = 258, code_size = 9;
    bool have_prev = false;
    // Track the decoder's dictionary growth separately: its additions lag
    // the encoder by one emitted code, including the final code before EOI.
    auto emit = [&](int code) {
        bw.code(code, code_size);
        if (have_prev) {
            if (decoder_next < 4096) ++decoder_next;
            if (decoder_next == (1 << code_size) && code_size < 12) ++code_size;
        }
        have_prev = true;
    };
    auto reset = [&]() {
        bw.code(clear, code_size);
        dictionary.clear();
        next = decoder_next = 258;
        code_size = 9;
        have_prev = false;
    };
    reset();
    if (!indices.empty()) {
        int prefix = indices[0];
        for (size_t i = 1; i < indices.size(); ++i) {
            uint8_t value = indices[i];
            uint32_t key = (static_cast<uint32_t>(prefix) << 8) | value;
            auto found = dictionary.find(key);
            if (found != dictionary.end()) {
                prefix = found->second;
                continue;
            }
            emit(prefix);
            if (next < 4096) dictionary.emplace(key, next++);
            else reset();
            prefix = value;
        }
        emit(prefix);
    }
    bw.code(eoi, code_size);
    bw.finish();
    return bw.bytes;
}

static void push_subblocks(std::vector<uint8_t>& out, const std::vector<uint8_t>& data) {
    size_t pos = 0;
    while (pos < data.size()) {
        size_t n = std::min<size_t>(255, data.size() - pos);
        out.push_back(static_cast<uint8_t>(n));
        out.insert(out.end(), data.begin() + static_cast<std::ptrdiff_t>(pos), data.begin() + static_cast<std::ptrdiff_t>(pos + n));
        pos += n;
    }
    out.push_back(0);
}

std::vector<uint8_t> encode_gif(const std::vector<Canvas>& frames, int delay_cs) {
    std::vector<uint8_t> out;
    if (frames.empty()) return out;
    int width = frames[0].width;
    int height = frames[0].height;
    std::vector<Color> pal = palette();
    out.insert(out.end(), {'G','I','F','8','9','a'});
    push_u16(out, width);
    push_u16(out, height);
    out.push_back(0xF7);
    out.push_back(0);
    out.push_back(0);
    for (Color c : pal) {
        out.push_back(c.r);
        out.push_back(c.g);
        out.push_back(c.b);
    }
    if (frames.size() > 1) {
        out.insert(out.end(), {0x21, 0xFF, 0x0B});
        out.insert(out.end(), {'N','E','T','S','C','A','P','E','2','.','0'});
        out.insert(out.end(), {0x03, 0x01, 0x00, 0x00, 0x00});
    }
    std::unordered_map<uint32_t, uint8_t> cache;
    for (const Canvas& frame : frames) {
        std::vector<uint8_t> indices;
        indices.reserve(frame.pixels.size());
        for (Color c : frame.pixels) indices.push_back(nearest_palette(c, pal, cache));
        out.insert(out.end(), {0x21, 0xF9, 0x04, 0x00});
        push_u16(out, std::max(1, delay_cs));
        out.insert(out.end(), {0x00, 0x00});
        out.push_back(0x2C);
        push_u16(out, 0);
        push_u16(out, 0);
        push_u16(out, width);
        push_u16(out, height);
        out.push_back(0x00);
        out.push_back(8);
        push_subblocks(out, lzw(indices));
    }
    out.push_back(0x3B);
    return out;
}

static std::string clipped(std::string s, int max_chars) {
    if (max_chars <= 0) return {};
    if (static_cast<int>(s.size()) <= max_chars) return s;
    if (max_chars <= 3) return s.substr(0, static_cast<size_t>(max_chars));
    return s.substr(0, static_cast<size_t>(max_chars - 3)) + "...";
}

Canvas render_dashboard(const Dashboard& dash, int frame_index) {
    const Config& cfg = dash.config();
    const Style& s = cfg.style;
    Canvas c = make_canvas(cfg.width, cfg.height, s.background);
    int m = s.margin;
    int full_w = cfg.width - m * 2;
    fill_rect(c, 0, 0, cfg.width, 72, s.panel);
    fill_rect(c, 0, 71, cfg.width, 1, s.border);
    draw_text(c, m, 18, cfg.title ? cfg.title : "FTGD", s.text, 3);
    draw_text(c, m, 50, clipped(dash.url(), std::max(8, full_w / (6 * s.font_scale))).c_str(), s.text_dim, s.font_scale);
    int y = 92;
    int stat_x = m;
    int stat_count = 0;
    for (const Widget& w : dash.widgets()) {
        if (w.kind != WidgetKind::Stat) continue;
        int card_w = (full_w - s.gap * 2) / 3;
        int x = stat_x + stat_count * (card_w + s.gap);
        fill_rect(c, x, y, card_w, 74, s.panel);
        stroke_rect(c, x, y, card_w, 74, s.border);
        fill_rect(c, x, y, 4, 74, w.color);
        draw_text(c, x + 16, y + 14, clipped(w.a, (card_w - 28) / (6 * s.font_scale)), s.text_dim, s.font_scale);
        draw_text(c, x + 16, y + 40, clipped(w.b, (card_w - 28) / (6 * 3)), s.text, 3);
        ++stat_count;
        if (stat_count == 3) {
            stat_count = 0;
            y += 86;
        }
    }
    if (stat_count != 0) y += 86;
    for (const Widget& w : dash.widgets()) {
        if (w.kind == WidgetKind::Stat) continue;
        if (y > cfg.height - 60) break;
        if (w.kind == WidgetKind::Separator) {
            fill_rect(c, m, y + 8, full_w, 1, s.border);
            y += 20;
        } else if (w.kind == WidgetKind::Text) {
            int scale = w.value > 0.5f ? 3 : s.font_scale;
            draw_text(c, m, y, clipped(w.a, full_w / (6 * scale)), w.value > 0.5f ? s.text : s.text_dim, scale);
            y += (7 * scale) + 12;
        } else if (w.kind == WidgetKind::Progress) {
            int bar_w = full_w;
            draw_text(c, m, y, clipped(w.a, full_w / (6 * s.font_scale)), s.text_dim, s.font_scale);
            y += 22;
            fill_rect(c, m, y, bar_w, 18, s.panel_alt);
            int fill_w = static_cast<int>(bar_w * w.value);
            if (cfg.animated && frame_index & 1) fill_w = std::max(0, fill_w - 10);
            fill_rect(c, m, y, fill_w, 18, w.color);
            stroke_rect(c, m, y, bar_w, 18, s.border);
            y += 34;
        } else if (w.kind == WidgetKind::Image) {
            int iw = w.image_width > 0 ? w.image_width : std::min(full_w, w.image.width);
            int ih = w.image_height > 0 ? w.image_height : w.image.height;
            iw = std::min(iw, full_w);
            ih = std::min(ih, cfg.height - y - 30);
            fill_rect(c, m, y, iw, ih, s.panel_alt);
            blit_image(c, w.image, m, y, iw, ih);
            stroke_rect(c, m, y, iw, ih, s.border);
            y += ih + 14;
        }
    }
    if (cfg.show_help) {
        int help_h = 112;
        int help_y = cfg.height - help_h - m;
        fill_rect(c, m, help_y, full_w, help_h, s.panel);
        stroke_rect(c, m, help_y, full_w, help_h, s.border);
        draw_text(c, m + 16, help_y + 14, "AVAILABLE DISCORD COMMANDS", s.text, s.font_scale);
        int cy = help_y + 40;
        int shown = 0;
        for (const Command& cmd : dash.commands()) {
            if (shown >= 3) break;
            std::string line = cmd.syntax;
            if (!cmd.label.empty()) line += "  " + cmd.label;
            if (!cmd.help.empty()) line += " - " + cmd.help;
            draw_text(c, m + 16, cy, clipped(line, (full_w - 32) / (6 * s.font_scale)), s.text_dim, s.font_scale);
            cy += 22;
            ++shown;
        }
        if (dash.commands().empty()) {
            draw_text(c, m + 16, cy, "ADD ftgd::link(...) OR ftgd::command(...) TO SHOW CONTROLS", s.text_dim, s.font_scale);
        }
    }
    return c;
}

} // namespace detail

} // namespace ftgd

#endif // FTGD_IMPLEMENTATION
