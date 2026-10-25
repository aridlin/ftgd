#!/usr/bin/env python3
"""Persistent FTGD GIF menus, controlled by Discord s/old/new message edits."""
import argparse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import re
import secrets
import sqlite3
import subprocess
import textwrap
import tempfile
from io import BytesIO
from PIL import Image
from urllib.parse import unquote, urlsplit

from render import render_counter, THEMES

ROOT = Path(__file__).resolve().parents[2]
UNITS = ('days', 'hours', 'minutes', 'seconds', 'milliseconds', 'microseconds')
DEFAULTS = dict(unit='days', value='0', theme='yellow',
    note='this is a static image so we can save resources, there is no need for a live update because kiko shits himself every day',
    star='NO UPDATE NEEDED')
PRESETS = {
    'days': DEFAULTS,
    'hours': dict(unit='hours', value='0', theme='blue',
        note='huh well i guess we gotta shorten it even more for it to indicate anything. Still static though', star='NOW IN HOURS!'),
    'microseconds': dict(unit='microseconds', value='1', theme='purple',
        note='wow that was a while', star='NEW RECORD!'),
}

def validate(config):
    if set(config) != set(DEFAULTS):
        raise ValueError('Invalid counter fields')
    if config['unit'] not in UNITS or config['theme'] not in THEMES:
        raise ValueError('Unknown unit or theme')
    value = str(config['value'])
    if not re.fullmatch(r'\d{1,12}(?:\.\d{1,6})?', value):
        raise ValueError('Use a nonnegative number: up to 12 digits and 6 decimals')
    try:
        if not Decimal(value).is_finite():
            raise ValueError('Invalid value')
    except InvalidOperation:
        raise ValueError('Invalid value') from None
    for field, limit in (('note', 180), ('star', 32)):
        text = config[field]
        if not isinstance(text, str) or len(text) > limit or any(ord(c) < 32 or ord(c) == 127 for c in text):
            raise ValueError(f'{field}: maximum {limit} characters, no control characters')
    return dict(config, value=value)

class Store:
    def __init__(self, path, base_url, renderer=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip('/')
        self.renderer = renderer or ROOT / 'build/counter-menu'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS collections(id TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS pages(
                    collection TEXT, id TEXT, screen TEXT, config TEXT, action TEXT,
                    body BLOB, PRIMARY KEY(collection,id));
                CREATE TABLE IF NOT EXISTS saved(
                    id TEXT PRIMARY KEY, collection TEXT, config TEXT, gif BLOB,
                    favourite INTEGER NOT NULL DEFAULT 0,
                    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def node(self, db, collection, screen, config, action=None, ident=None):
        ident = ident or secrets.token_hex(4)
        db.execute('INSERT INTO pages VALUES(?,?,?,?,?,NULL)',
            (collection, ident, screen, json.dumps(config), json.dumps(action)))
        return ident

    def new_collection(self):
        collection = secrets.token_hex(16)
        with self.connect() as db:
            db.execute('INSERT INTO collections VALUES(?)', (collection,))
            self.node(db, collection, 'settings', DEFAULTS, ident='p')
        return collection

    def url(self, collection, page='p'):
        return f'{self.base_url}/count/gifmenu/{collection}/{page}.gif'

    def input_page(self, db, collection, token):
        parent, field, value = token.split('~', 2)
        if field not in ('value', 'note', 'star'):
            raise ValueError('Unknown input field')
        old = db.execute('SELECT * FROM pages WHERE collection=? AND id=?', (collection, parent)).fetchone()
        if old is None:
            raise KeyError('Unknown source page')
        config = json.loads(old['config'])
        config[field] = '' if value == 'EMPTY' and field != 'value' else value.replace('_', ' ')
        config = validate(config)
        self.node(db, collection, 'settings' if field == 'value' else 'notes', config, ident=token)
        return db.execute('SELECT * FROM pages WHERE collection=? AND id=?', (collection, token)).fetchone()

    def page(self, collection, token):
        if not re.fullmatch('[0-9a-f]{32}', collection) or len(token) > 700:
            raise ValueError('Invalid menu address')
        with self.connect() as db:
            # Actions, their result GIF and all destination tokens commit together.
            # Discord can fetch the same URL many times without saving duplicates.
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM collections WHERE id=?', (collection,)).fetchone():
                raise KeyError('Unknown collection')
            row = db.execute('SELECT * FROM pages WHERE collection=? AND id=?', (collection, token)).fetchone()
            if row is None and token.count('~') >= 2:
                row = self.input_page(db, collection, token)
            if row is None:
                raise KeyError('Unknown page')
            if row['body'] is not None:
                return bytes(row['body'])
            config, action = json.loads(row['config']), json.loads(row['action'])
            screen = row['screen']
            if action and action.get('kind') == 'save':
                saved_id = secrets.token_hex(16)
                db.execute('INSERT INTO saved(id,collection,config,gif) VALUES(?,?,?,?)',
                    (saved_id, collection, json.dumps(config), render_counter(config)))
                action = dict(kind='view', id=saved_id)
            elif action and action.get('kind') == 'favourite':
                result = db.execute('UPDATE saved SET favourite=? WHERE collection=? AND id=?',
                    (int(action['value']), collection, action['id']))
                if result.rowcount != 1:
                    raise KeyError('Unknown saved GIF')
                action = dict(kind='view', id=action['id'])
            if '~' in token:
                # A long custom note makes the edited URL too long to repeat in
                # substitution controls. Give the user a short continuation URL.
                short = self.node(db, collection, screen, config)
                lines = [('H', 'VALUE UPDATED'),
                         ('T', 'Send this short menu URL to continue:'),
                         ('T', self.url(collection, short))]
            else:
                lines = self.menu(db, collection, token, screen, config, action)
            body = self.render_menu(collection, token, lines)
            db.execute('UPDATE pages SET body=? WHERE collection=? AND id=?', (body, collection, token))
            return body

    def render_menu(self, collection, token, lines):
        with tempfile.TemporaryDirectory(prefix='ftgd-preview-') as tmp:
            prepared = []
            for kind, text in lines:
                if kind == 'I':
                    path = Path(tmp) / 'preview.ppm'
                    Image.open(BytesIO(render_counter(json.loads(text)))).convert('RGB').save(path)
                    text = str(path)
                prepared.append(kind + '\t' + text)
            data = '\n'.join(prepared) + '\n'
            result = subprocess.run([str(self.renderer), self.base_url, collection, token],
                input=data.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=True)
        if not result.stdout.startswith(b'GIF89a'):
            raise RuntimeError('Menu renderer did not return a GIF')
        # FTGD's dependency-free encoder is deliberately simple. Repack its
        # exact pixels using Pillow's LZW compression for Discord-sized menus.
        packed = BytesIO()
        with Image.open(BytesIO(result.stdout)) as image:
            image.save(packed, 'GIF', optimize=True)
        return packed.getvalue()

    def menu(self, db, collection, token, screen, config, action):
        lines = []
        def text(value):
            # FTGD's font is ASCII; counter art supports Unicode via Pillow.
            value = value.encode('ascii', 'replace').decode()
            lines.extend(('T', part) for part in textwrap.wrap(value, 94) or [''])
        def heading(value):
            lines.append(('H', value))
        def link(label, target, cfg=None, act=None):
            dest = self.node(db, collection, target, cfg or config, act)
            # Include .gif in both sides, avoiding a token matching the collection.
            text(f's/{token}.gif/{dest}.gif  {label}')
        def custom(field, placeholder):
            text(f's/{token}.gif/{token}~{field}~{placeholder}.gif')
        def config_line():
            text(f"{config['value']} {config['unit']} | theme: {config['theme']}")
        if screen == 'settings':
            heading('1 / 3 - COUNTER SETTINGS')
            config_line()
            text('Send the commands below in Discord to edit your GIF message.')
            text('Quick presets (these also reset both notes):')
            for name, preset in PRESETS.items():
                link(name.upper(), 'settings', dict(preset))
            text('Change just the measurement unit:')
            for unit in UNITS:
                if unit != config['unit']:
                    link(unit, 'settings', dict(config, unit=unit))
            text('Set elapsed amount: replace NUMBER with e.g. 0, 1, 12 or 0.5')
            custom('value', 'NUMBER')
            text('Changing unit keeps the number: this is a meme label, not conversion.')
            for theme in THEMES:
                if theme != config['theme']:
                    link('THEME ' + theme, 'settings', dict(config, theme=theme))
            link('NEXT: NOTES', 'notes')
            link('SAVED GIFS', 'library')
            link('FAVOURITES', 'favourites')
        elif screen == 'notes':
            heading('2 / 3 - NOTES')
            config_line()
            text('Technical note: ' + (config['note'] or '(empty)'))
            text('Star note: ' + (config['star'] or '(empty)'))
            text('Replace TEXT with your words. Use underscores for spaces.')
            text('Use EMPTY to remove a note. No slashes; percent-encode special characters.')
            text('Technical note: up to 180 characters.')
            custom('note', 'TEXT')
            text('Star note: up to 32 characters.')
            custom('star', 'TEXT')
            link('NEXT: PREVIEW AND SAVE', 'preview')
            link('BACK: SETTINGS', 'settings')
        elif screen == 'preview':
            heading('3 / 3 - PREVIEW AND SAVE')
            config_line()
            lines.append(('I', json.dumps(config)))
            text('Technical note: ' + (config['note'] or '(empty)'))
            text('Star note: ' + (config['star'] or '(empty)'))
            text('A static snapshot, with deep fry outside the readable notes.')
            link('CREATE AND SAVE GIF', 'saved', act=dict(kind='save'))
            link('BACK: NOTES', 'notes')
            link('BACK: SETTINGS', 'settings')
        elif screen in ('library', 'favourites'):
            heading('FAVOURITES' if screen == 'favourites' else 'SAVED GIFS')
            offset = max(0, int((action or {}).get('offset', 0)))
            query = 'SELECT * FROM saved WHERE collection=?'
            if screen == 'favourites':
                query += ' AND favourite=1'
            rows = db.execute(query + ' ORDER BY created DESC,rowid DESC LIMIT 7 OFFSET ?', (collection, offset)).fetchall()
            if not rows:
                text('Nothing saved here yet.')
            for row in rows[:6]:
                item = json.loads(row['config'])
                label = f"{'* ' if row['favourite'] else ''}{item['value']} {item['unit']} / {item['theme']} / {row['id'][:8]}"
                link(label, 'saved', item, dict(kind='view', id=row['id']))
            if offset:
                link('PREVIOUS PAGE', screen, act=dict(offset=max(0, offset-6)))
            if len(rows) > 6:
                link('NEXT PAGE', screen, act=dict(offset=offset+6))
            link('REFRESH LIST', screen, act=dict(offset=offset))
            link('ALL SAVED GIFS' if screen == 'favourites' else 'FAVOURITES', 'library' if screen == 'favourites' else 'favourites')
            link('CREATE ANOTHER', 'settings', dict(DEFAULTS))
        elif screen == 'saved':
            row = db.execute('SELECT * FROM saved WHERE collection=? AND id=?', (collection, action['id'])).fetchone()
            if row is None:
                raise KeyError('Unknown saved GIF')
            heading('GIF SAVED')
            config_line()
            text('Send this permanent GIF URL in Discord:')
            text(f"{self.base_url}/count/g/{row['id']}.gif")
            text('Or turn this menu message into the GIF:')
            text(f"s/{token}.gif/raw-{row['id']}.gif")
            text('Open that GIF in Discord and use its star to favourite it there.')
            text('The menu also has its own favourites list:')
            link('REMOVE FROM FAVOURITES' if row['favourite'] else 'ADD TO FAVOURITES', 'saved',
                 act=dict(kind='favourite', id=row['id'], value=not row['favourite']))
            link('SAVED GIFS', 'library')
            link('FAVOURITES', 'favourites')
            link('MAKE A VARIATION', 'settings')
        else:
            raise ValueError('Unknown screen')
        return lines

    def get(self, path):
        parts = urlsplit(path).path.strip('/').split('/')
        if not parts or parts.pop(0) != 'count':
            raise KeyError('Unknown route')
        if len(parts) == 2 and parts[0] == 'g' and re.fullmatch(r'[0-9a-f]{32}\.gif', parts[1]):
            with self.connect() as db:
                row = db.execute('SELECT gif FROM saved WHERE id=?', (parts[1][:-4],)).fetchone()
                if row is None:
                    raise KeyError('Unknown GIF')
                return bytes(row['gif'])
        if len(parts) == 3 and parts[0] == 'gifmenu' and parts[2].endswith('.gif'):
            collection, token = parts[1], unquote(parts[2][:-4])
            with self.connect() as db:
                if re.fullmatch('raw-[0-9a-f]{32}', token):
                    row = db.execute('SELECT gif FROM saved WHERE collection=? AND id=?', (collection, token[4:])).fetchone()
                    if row is None:
                        raise KeyError('Unknown GIF')
                    return bytes(row['gif'])
            return self.page(collection, token)
        raise KeyError('Unknown route')

def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/healthz':
                body, status, kind = b'ok\n', 200, 'text/plain'
            else:
                try:
                    body, status, kind = store.get(self.path), 200, 'image/gif'
                except KeyError:
                    body, status, kind = b'Not found\n', 404, 'text/plain'
                except ValueError as exc:
                    body, status, kind = (str(exc) + '\n').encode(), 400, 'text/plain'
                except (subprocess.SubprocessError, RuntimeError, sqlite3.Error):
                    body, status, kind = b'Could not render this menu; try again.\n', 503, 'text/plain'
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable' if status == 200 and kind == 'image/gif' else 'no-store')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        do_HEAD = do_GET

        def log_message(self, fmt, *args):
            # Menu URLs contain a private collection capability: do not log them.
            pass
    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--base-url', default='http://127.0.0.1:8765')
    parser.add_argument('--data', type=Path, default=ROOT / 'build/counter-data.sqlite3')
    parser.add_argument('--new-menu', action='store_true', help='Print a new private collection URL and exit')
    args = parser.parse_args()
    base = urlsplit(args.base_url)
    if base.scheme not in ('http', 'https') or not base.netloc or base.query or base.fragment or base.path not in ('', '/'):
        parser.error('--base-url must be an HTTP(S) origin without a path or query')
    store = Store(args.data, args.base_url)
    if args.new_menu:
        print(store.url(store.new_collection()))
        return
    if not store.renderer.exists():
        parser.error('Build the renderer first: make counter-menu')
    print(f'Listening on {args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), handler_for(store)).serve_forever()

if __name__ == '__main__':
    main()
