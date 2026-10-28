# Counter and meter studio + Discord GIF menus

## Meters: reading in the URL

Choose **Meter** in the website's Module selector, or **METER MODULE** in the
Discord GIF menu. Styles: thermometer, ruler, progress bar. The default is a
0–100% “horny meter”; title, range, reading, suffix, theme and notes are editable.
Meters have animated sparkles but their readings do not count up.

The finished link is:

```text
/count/m/<saved-id>/75/<seed>.gif
```

Change just `/75/` to `/20/` for a reading of 20. Different value URLs can coexist
and do not modify the template, its favourite status, or any timer. The website's
**Reading in the URL** control does the same thing and updates the copyable link.
Saved meters appear in the same searchable/favouritable collection as counters.

Values and range endpoints support signed numbers with up to 12 integer digits
and 6 decimals. The maximum must exceed the minimum; values outside the range
return HTTP 400. The unit is an optional suffix (up to 16 characters). GIF menu
edits also support `.minimum=`, `.maximum=` and `.unit=`; `EMPTY` clears the unit.
URL-encode literal dots before any reserved field name when entering free text.
Raw meter URLs always return GIF bytes, even in a browser. Up to 64 value/seed
renders are cached per saved template revision. Changing a value creates a fresh
Discord image URL; change the seed as well if you need to bypass a client cache.

## Time counters

A browser creator and FTGD menu app that save animated counter GIFs. Stars and
clock hands animate in both modes:

- **Count up:** elapsed time since creation plus the initial offset, in the
  chosen unit. A reset restarts from now with zero offset.
- **Static:** the number stays fixed while the artwork animates. Reset sets it
  to zero; it stays in static mode.

The website ticks continuously. GIFs capture the current value when fetched and
loop their artwork; a downloaded GIF cannot contact the server to keep counting.
Change the URL seed to refresh a cached Discord image. Seed changes never reset
start times or replay save/reset actions.

## Run

Requires C++17, Python 3.10+, Pillow, and DejaVu Sans fonts.

```sh
make counter-menu
make counter-test
python3 examples/counter_menu/server.py --new-menu
python3 examples/counter_menu/server.py
```

Pass the same `--data` and `--base-url` to both server commands. For example:

```sh
python3 examples/counter_menu/server.py --base-url https://your-host.example --data /var/lib/kiko-counter/data.sqlite3 --port 8793
```

Proxy `/count/*` to the server, preserving paths. The listener defaults to
loopback; `/healthz` is its internal health check. Back up SQLite through its
backup API. Don't run `make clean` on a database in `build/` that you want to keep.

## Browser creator

Open `/count/` for a per-browser collection remembered with an HttpOnly cookie.
Creator URLs requested with `Accept: text/html` show the website, including the
form, animated preview, search, favourites, reset and share controls. Discordbot
and image requests still receive GIF bytes. `?format=gif` explicitly opens the
GIF menu in a browser. Responses vary on Accept and User-Agent.

The website uses normal spaces. The timer starts when the counter is created,
not when a preview is shown. The supplied value is the initial offset for a
counting counter, or the fixed number for static mode. Saved GIFs, favourites,
start times and reset state survive restarts.

## Discord controls and seed URLs

Creator URL:

```text
/count/gifmenu/<collection>/v2/<seed>/~.gif
```

The seed can be any label up to 200 characters. URL-encode special characters
(including `~` as `%7E`) in the seed so the navigation marker stays unambiguous.
The website does this automatically. Change just the seed for fresh rendering.

1. Send the menu URL as your own message. Follow commands like `s/~/1~`.
2. Choose preset, unit, mode, subject, initial offset/fixed value and theme.
   Presets preserve the subject; days/hours default to counting, microseconds
   to static. Changing units preserves the configured numeric value.
3. Edit fields using the displayed commands, e.g. `s/~/-~.subject=kill` or
   `s/~/-~.value=0.5`. The dash records edit order. Underscores become spaces;
   every letter and literal tilde is preserved. `EMPTY` clears a note.
   Limits: subject 80 characters, technical note 180, star note 32.
   URL-encode `/`, `?`, `#` and `%`. Encode the dot if literal text contains
   `.subject=`, `.value=`, `.note=`, or `.star=`.
4. Preview, create and save. Open any saved item from the library/favourites to
   view its GIF, favourite it, reset time to zero or make a variation.

Saved GIF URL:

```text
/count/g/<saved-id>/<seed>.gif
```

The unseeded `/count/g/<saved-id>.gif` route fetches the latest value. Seeded
counting renders are cached in a bounded cache (64 snapshots per saved revision).
Reset increments the revision; the website returns a fresh image URL. Discord
can retain old image bytes, so use a new seed after resetting there.

## Persistence and ownership

The collection's secret URL is its edit capability. Anyone with it can browse
and modify that collection. Share saved GIF URLs to share only an image.
There is no public collection-list endpoint and the app does not log requests.

Menu actions and their completed results commit atomically. Repeated requests,
HEAD requests and seed changes do not repeat a save or reset. Website mutations
also have idempotency keys and check ownership. Seed refreshes allocate distinct
menu destinations when library contents or actions change. Legacy saved files
remain byte-identical until explicitly reset; old menu entry URLs open the new
creator. The website API is `/count/api/<collection>`.

Rendering uses DejaVu Sans and high-contrast landscape menus. New counter GIFs
have 12 frames over three seconds, a shared 64-colour palette and limited moving
regions. Menus use 8 colours (32 with preview). Rendering concurrency is bounded.

## Deployment

`kiko-counter.service` uses a dedicated unprivileged account and persistent
`/var/lib/kiko-counter`. Set the public origin in ExecStart.
`Caddyfile.fragment` belongs inside the existing site block. GIF routes must be
fetchable without site login for Discord's image proxy.
