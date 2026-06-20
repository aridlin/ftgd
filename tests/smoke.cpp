#define FTGD_IMPLEMENTATION
#include "../ftgd.hpp"

#include <cassert>
#include <string>

int main() {
    ftgd::Config cfg;
    cfg.width = 480;
    cfg.height = 320;
    cfg.base_url = "https://website.com";
    cfg.app_name = "appname";
    cfg.page = "p";

    ftgd::Dashboard dash(cfg);
    dash.begin();
    dash.stat("PAGE", "p");
    dash.text("hello from ftgd");
    dash.link("next", "1p");
    dash.end();

    assert(dash.url() == "https://website.com/appname/p.gif");
    assert(dash.url_for("1p") == "https://website.com/appname/1p.gif");
    assert(ftgd::command_s("p", "1p") == "s/p/1p");
    assert(ftgd::apply_command("p", "s/p/1p") == "1p");
    assert(ftgd::apply_commands("p", {"s/p/1p", "s/1p/11p"}) == "11p");
    assert(ftgd::page_from_url("https://website.com/appname/1p.gif", cfg) == "1p");

    std::vector<uint8_t> gif = dash.gif();
    assert(gif.size() > 32);
    assert(gif[0] == 'G' && gif[1] == 'I' && gif[2] == 'F');
    assert(gif.back() == 0x3B);
    return 0;
}
