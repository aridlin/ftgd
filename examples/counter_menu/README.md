# Kiko counter GIF menu

An FTGD menu app for Discord's `s/old/new` message editing. The menu and its
preview are GIFs; there is no bot token, JavaScript UI, or Discord account login.
The generated meme is a static snapshot with the selected elapsed amount.

## Run

Requires C++17, Python 3.10+, Pillow, and DejaVu Sans fonts.

```sh
make counter-menu
make counter-test
python3 examples/counter_menu/server.py --new-menu
python3 examples/counter_menu/server.py
```

The `--new-menu` command prints a private collection URL. Open it locally for testing.
For Discord, expose the service through HTTPS and pass the **same** public origin
and database to both commands:

```sh
python3 examples/counter_menu/server.py --base-url https://your-host.example --data /var/lib/kiko-counter/data.sqlite3 --new-menu
python3 examples/counter_menu/server.py --base-url https://your-host.example --data /var/lib/kiko-counter/data.sqlite3 --port 8793
```

Proxy `/count/*` to this process, preserving the path. The default listener is
loopback only. `GET /healthz` is the internal health check. Back up the SQLite
database using SQLite's backup API; it contains both metadata and actual GIFs.
Do not use `make clean` against a database stored in `build/` that you want to keep.

## Use in Discord

The public `/count/` entry opens a separate collection for each browser and
remembers it in an HttpOnly cookie. It redirects to that collection's GIF URL;
copy the resulting URL into Discord. The index can link to this entry without
publishing anyone's private collection capability. Clearing cookies starts a
new collection; saved private URLs continue to work.

1. Send the private menu URL as your own Discord message. Follow the displayed
   `s/~/1~` commands. The `.gif` extension stays in place, and every ordinary
   navigation command replaces only the first `~`, including after custom edits.
2. **Settings:** choose a preset, unit, subject, amount and theme. Defaults are
   days, 0, `kiko shat himself`, yellow, the original technical note and
   `NO UPDATE NEEDED`. Presets preserve your subject and reset other fields.
   `s/~/~.subject=kill` changes the heading to `DAYS SINCE KILL`.
   `s/~/~.value=0.5` sets the number. Changing units keeps the number.
3. **Notes:** use `s/~/~.note=TEXT` or `s/~/~.star=TEXT`. Underscores become
   spaces; `EMPTY` clears a note. Every letter is entered normally, including `b`.
   Tildes in entered text stay literal; there is no character substitution. Limits: subject 80, note 180, star 32 characters.
   Encode `/`, `?`, `#`, and literal `%` as `%2F`, `%3F`, `%23`, and `%25`.
   Ordinary periods are fine. Encode the dot as `%2E` if your literal text
   includes `.subject=`, `.value=`, `.note=`, or `.star=`.
4. **Preview and save:** inspect the actual image and choose Create and Save.
   The saved screen gives a permanent GIF URL and a short Show the GIF command.
   Favourite it in Discord or use the menu's separate favourites list.

Saved GIFs and favourites survive service restarts. Lists show six items per page
and have previous/next/refresh controls. Old menus are immutable snapshots: use
Refresh List to see later additions. The original menu URL remains usable.
Return to it by sending it again after turning a menu message into a raw GIF.

## Cache and ownership model

Every navigation destination is a distinct URL. Choices insert one character
before the first `~`, while custom input is inserted after it. Entered letters
cannot steal the navigation replacement. A new input is applied to its source
page once; later choices use the resulting state, so presets can override old
input values. Pages commit their GIF, destinations and actions atomically.
Repeated GET/HEAD requests do not duplicate saves or favourite changes.

Menus use `/count/gifmenu/<collection>/v2/~.gif`. The versioned route and
`pages_v2` table avoid conflicts with old immutable cached menus. Old `p.gif`
and `b.gif` entries (including v2) redirect to the new root; saved GIFs and favourites are
shared with the previous version and their bytes are preserved. Collection
secrets retain their reversible b-free alphabet.

The collection's 128-bit secret URL is its edit capability. Anyone with it can
browse and modify that collection. Share `/count/g/<id>.gif` URLs to share only an
image, and keep menu URLs private. There is no collection-list endpoint.
Requests are not logged by the app.

Pillow draws wide, short menus with DejaVu Sans TrueType fonts, bright text
on a dark background, and two or three columns. FTGD compresses the complete
image using LZW; Pillow reduces menus to 8 colours (32 with previews), retaining
readable text while reducing transfer size. New saved memes use 64 colours. The bitmap
menu font is not used. Only the meme artwork gets compression damage, with a
lighter pass on the notes. All rendering is local; user text is never run
through a shell or interpreted as markup.

## Deployment files

`kiko-counter.service` uses a dedicated unprivileged account and persistent
`/var/lib/kiko-counter`. Set the origin for your host in its ExecStart.
`Caddyfile.fragment` belongs inside the existing site block. These routes need
to be fetchable without HTTP basic auth for Discord's image proxy.
