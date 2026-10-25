# FTGD

FTGD is a single-header C++17 dashboard library for Discord-embeddable GIF dashboards.

It follows the immediate-mode feel of `ft.hpp`, but instead of opening a GUI/TUI/web server it returns GIF bytes. The intended control loop is:

```text
https://website.com/appname/p.gif
s/p/1p
https://website.com/appname/1p.gif
```

The `p` page token is configurable through `ftgd::Config`, and Discord `s/x/y` commands are first-class helpers.

## Quick Start

```cpp
#define FTGD_IMPLEMENTATION
#include "ftgd.hpp"

int main() {
    ftgd::Config cfg;
    cfg.title = "FTGD STATUS";
    cfg.base_url = "https://website.com";
    cfg.app_name = "appname";
    cfg.page = "p";

    ftgd::create_dashboard(cfg);
    ftgd::begin("p");
    ftgd::stat("USERS", "128");
    ftgd::text("GIF dashboard controlled from Discord.");
    ftgd::link("OPEN PAGE 1p", "1p");
    ftgd::end();

    auto response = ftgd::response(); // content_type=image/gif, body=GIF bytes
    ftgd::shutdown();
}
```

## API Shape

- `ftgd::Config` controls size, title, base URL, app path, page token, suffix, style, and animation.
- `ftgd::begin()` / `ftgd::end()` clear and finish the current frame.
- `ftgd::stat()`, `ftgd::text()`, `ftgd::heading()`, `ftgd::progress()`, and `ftgd::image()` add dashboard content.
- `ftgd::link(label, to)` creates a visible Discord command from the current page to another page.
- `ftgd::command(label, from, to)` creates an explicit `s/from/to` command.
- `ftgd::gif()` returns raw GIF bytes.
- `ftgd::response()` returns `{ "image/gif", bytes }` for small HTTP adapters.

## Build

### Counter GIF menu app

[`examples/counter_menu`](examples/counter_menu/README.md) is a complete hosted
GIF menu: three configuration screens, a counter preview, persistent saved GIFs,
and favourites. It uses Discord's `s/old/new` edits and stable image URLs, with
days/hours/microseconds presets. Build with `make counter-menu`; run its tests
with `make counter-test`.

```bash
make
make test
```

The example writes `build/basic.gif`.

## Notes

FTGD intentionally has no runtime dependencies. It includes a tiny bitmap font renderer, simple PPM/raw-RGBA image support, and a GIF89a encoder with a fixed palette. That keeps it easy to embed in bots, tiny HTTP handlers, and single-file tools.
