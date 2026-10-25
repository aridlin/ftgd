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

1. Send the private menu URL as your own message. Type one of the displayed
   `s/b/1b` commands to edit your most recent message containing it.
2. **Settings:** choose a preset, unit, amount and theme. Defaults are days, 0,
   yellow, the original static-image technical note and `NO UPDATE NEEDED`.
   Hours and microseconds presets reproduce the other two jokes. Changing only
   the unit keeps the number rather than converting a duration.
3. **Notes:** optionally replace either note. Use underscores for spaces,
   `EMPTY` to clear it, and percent encoding for special characters. Limits:
   technical note 180 characters; star note 32. Encode slashes as `%2F` and
   tildes as `%7E`. Input commands look like `s/b/~n~TEXT~~b`; subsequent
   commands use the final `~~b` separator so letters in your note cannot
   interfere. Keep following the displayed commands without resending a URL.
4. **Preview and save:** inspect the actual image and select Create and Save.
   The saved screen gives a permanent public GIF URL and a substitution command
   to turn the menu message into the raw GIF. Favourite that image in Discord,
   or use the menu's separate favourites list.

Saved GIFs and favourites survive service restarts. Lists show six items per page
and have previous/next/refresh controls. Old menus are immutable snapshots: use
Refresh List to see later additions. The original menu URL remains usable.
Return to it by sending it again after turning a menu message into a raw GIF.

## Cache and ownership model

Every navigation destination is a distinct URL. Choices append a short character
before the reusable final `b`, so ordinary controls always look like `s/b/1b`.
The `.gif` extension stays in place. Collection URLs use a reversible b-free
alphabet so substitutions cannot accidentally change the collection secret.
Old `/p.gif` entry links redirect to the updated `/b.gif` menu. Rendering a menu commits
its GIF and all destinations atomically. Save/favourite actions run once even if
Discord fetches the URL concurrently, retries, or sends HEAD before GET. Saved
image URLs never change their bytes; creating a variation produces another GIF.

The collection's 128-bit secret URL is its edit capability. Anyone with it can
browse and modify that collection. Share `/count/g/<id>.gif` URLs to share only an
image, and keep menu URLs private. There is no collection-list endpoint.
Requests are not logged by the app.

Pillow draws menus with DejaVu Sans TrueType fonts, bright text on a dark
background, and highlighted command cards. FTGD encodes the complete menu
image; Pillow repacks its GIF without changing the encoded pixels. The bitmap
menu font is not used. Only the meme artwork gets compression damage, with a
lighter pass on the notes. All rendering is local; user text is never run
through a shell or interpreted as markup.

## Deployment files

`kiko-counter.service` uses a dedicated unprivileged account and persistent
`/var/lib/kiko-counter`. Set the origin for your host in its ExecStart.
`Caddyfile.fragment` belongs inside the existing site block. These routes need
to be fetchable without HTTP basic auth for Discord's image proxy.
