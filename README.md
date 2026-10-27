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
GIF menu plus browser creator: configuration screens, animated counter previews,
persistent saved GIFs, elapsed-time clocks, resets, search and favourites. It uses Discord's `s/old/new` edits and stable image URLs, with
days/hours/microseconds presets and editable counter subjects. Its meter module
adds thermometer, ruler and progress-bar GIFs whose readings come from a single
URL segment (`/count/m/<id>/75/fresh.gif`). Build with `make counter-menu`; run its tests
with `make counter-test`.

```bash
make
make test
```

The example writes `build/basic.gif`.

## FTGD 0.2

GIF output now uses dictionary LZW compression, including 9–12 bit code widths
and dictionary resets. The existing dashboard API and palette are unchanged.
Run `make codec-test` (Python + Pillow) for independent pixel round trips and
animated-frame decoding, alongside `make test` for the C++ API smoke tests.

`ftgd::encode_image(image)` encodes an externally drawn `ftgd::Image`; this lets
applications use a TrueType rasterizer without depending on the built-in font.
The counter example uses Pillow/DejaVu Sans for landscape menu cards, then FTGD
for GIF encoding. This optional example does not add a library dependency.

`ftgd::append_command("1")` returns `s/~/1~`. Put the marker before any
user-entered text and keep the URL before it free of the marker. The replacement
retains the marker for the next command. The helper rejects empty markers,
slashes, and choices containing the marker; it does not validate the host URL.

## Notes

FTGD intentionally has no runtime dependencies. It includes a tiny bitmap font renderer, simple PPM/raw-RGBA image support, and a GIF89a encoder with a fixed palette. That keeps it easy to embed in bots, tiny HTTP handlers, and single-file tools.
