"""Saved counter clocks and idempotent actions, independent of GIF playback."""
import json
import secrets
import time
from decimal import Decimal, ROUND_DOWN
from urllib.parse import quote
from render import render_counter
from meter import reading

UNIT_SECONDS = {'days':86400, 'hours':3600, 'minutes':60, 'seconds':1,
                'milliseconds':.001, 'microseconds':.000001}

def current_config(row, now=None):
    config = json.loads(row['config'])
    config.setdefault('subject','kiko shat himself')
    config.setdefault('mode','static')
    if config.get('mode', 'static') == 'counting' and row['started'] is not None:
        elapsed = max(0, (time.time() if now is None else now) - row['started'])
        value = Decimal(row['offset']) + Decimal(str(elapsed))/Decimal(str(UNIT_SECONDS[config['unit']]))
        precision = Decimal('.0001') if config['unit'] in ('hours','days') else Decimal('.01')
        config['value'] = format(value.quantize(precision, rounding=ROUND_DOWN), 'f').rstrip('0').rstrip('.') if '.' in str(value.quantize(precision)) else str(value)
        if not config['value']: config['value']='0'
    return config

class LiveStore:
    def migrate_live(self, db):
        existing = {r['name'] for r in db.execute('PRAGMA table_info(saved)')}
        for name, definition in [('started','REAL'),('offset',"TEXT NOT NULL DEFAULT '0'"),
                                 ('revision','INTEGER NOT NULL DEFAULT 0'),('animated','INTEGER NOT NULL DEFAULT 0')]:
            if name not in existing:
                db.execute(f'ALTER TABLE saved ADD COLUMN {name} {definition}')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS snapshots(collection TEXT, token TEXT, seed TEXT, body BLOB,
                PRIMARY KEY(collection,token,seed));
            CREATE TABLE IF NOT EXISTS api_ops(collection TEXT, key TEXT, result TEXT,
                PRIMARY KEY(collection,key));
        ''')

    def create_saved(self, db, collection, config):
        ident = secrets.token_hex(16)
        started = self.clock()
        gif = render_counter(config, animated=True)
        db.execute('INSERT INTO saved(id,collection,config,gif,started,offset,animated) VALUES(?,?,?,?,?,?,1)',
                   (ident,collection,json.dumps(config),gif,started,config['value']))
        return ident

    def reset_saved(self, db, collection, ident):
        row = db.execute('SELECT * FROM saved WHERE collection=? AND id=?',(collection,ident)).fetchone()
        if row is None: raise KeyError('Unknown saved GIF')
        config = json.loads(row['config'])
        if config.get('module')=='meter': raise ValueError('Meters have no timer; edit the value in the GIF URL')
        config['value']='0'
        gif = render_counter(config, animated=True)
        db.execute('UPDATE saved SET started=?,offset=?,config=?,gif=?,revision=revision+1,animated=1 WHERE id=? AND collection=?',
                   (self.clock(),'0',json.dumps(config),gif,ident,collection))

    def saved_body(self, db, row, seed=None):
        config=json.loads(row['config'])
        if config.get('module')=='meter':
            return self.meter_body(db,row,config['value'],seed or 'default')
        # Old/static files remain byte-identical until explicitly reset.
        if json.loads(row['config']).get('mode','static') != 'counting':
            return bytes(row['gif'])
        key = f"gif:{row['id']}:{row['revision']}"
        if seed is not None:
            cached=db.execute('SELECT body FROM snapshots WHERE collection=? AND token=? AND seed=?',
                              (row['collection'],key,seed)).fetchone()
            if cached: return bytes(cached['body'])
        body=render_counter(current_config(row,self.clock()),animated=True)
        if seed is not None:
            db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)',(row['collection'],key,seed,body))
            db.execute('DELETE FROM snapshots WHERE collection=? AND token=? AND rowid NOT IN (SELECT rowid FROM snapshots WHERE collection=? AND token=? ORDER BY rowid DESC LIMIT 64)',(row['collection'],key,row['collection'],key))
        return body

    def meter_body(self, db, row, value, seed):
        config=json.loads(row['config'])
        if config.get('module')!='meter': raise KeyError('Unknown meter')
        config=reading(config,value)
        token=f"meter:{row['id']}:{row['revision']}:art-v2"
        cache_key=config['value']+'/'+seed
        cached=db.execute('SELECT body FROM snapshots WHERE collection=? AND token=? AND seed=?',
                          (row['collection'],token,cache_key)).fetchone()
        if cached: return bytes(cached['body'])
        body=render_counter(config,animated=True)
        db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)',(row['collection'],token,cache_key,body))
        db.execute('DELETE FROM snapshots WHERE collection=? AND token=? AND rowid NOT IN (SELECT rowid FROM snapshots WHERE collection=? AND token=? ORDER BY rowid DESC LIMIT 64)',
                   (row['collection'],token,row['collection'],token))
        return body

    def item(self, row):
        config=current_config(row,self.clock())
        result=dict(id=row['id'],config=config, favourite=bool(row['favourite']),
                    started=row['started'],offset=row['offset'],revision=row['revision'],animated=bool(row['animated']),
                    gif=f"{self.base_url}/count/g/{row['id']}.gif")
        if config.get('module')=='meter':
            result['gif']=f"{self.base_url}/count/m/{row['id']}/{config['value']}/fresh.gif"
            result['gif_template']=f"{self.base_url}/count/m/{row['id']}/{{value}}/{{seed}}.gif"
        return result

    def api_get(self, collection, query='', favourites=False):
        with self.connect() as db:
            if not db.execute('SELECT 1 FROM collections WHERE id=?',(collection,)).fetchone():
                raise KeyError('Unknown collection')
            rows=db.execute('SELECT * FROM saved WHERE collection=? ORDER BY created DESC,rowid DESC',(collection,)).fetchall()
            items=[self.item(r) for r in rows if (not favourites or r['favourite']) and query.casefold() in ' '.join(str(value) for value in json.loads(r['config']).values()).casefold()]
        return dict(items=items, now=self.clock(),menu=self.url(collection), defaults=self.defaults,presets=self.presets)

    def api_action(self, collection, payload):
        from server import validate
        action=payload.get('action')
        if action=='preview':
            with self.connect() as db:
                if not db.execute('SELECT 1 FROM collections WHERE id=?',(collection,)).fetchone(): raise KeyError('Unknown collection')
            return render_counter(validate(payload['config']),animated=True)
        key=payload.get('key','')
        if not isinstance(key,str) or not 8 <= len(key) <= 100: raise ValueError('An action key is required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM collections WHERE id=?',(collection,)).fetchone(): raise KeyError('Unknown collection')
            previous=db.execute('SELECT result FROM api_ops WHERE collection=? AND key=?',(collection,key)).fetchone()
            if previous: return json.loads(previous['result'])
            if action=='create':
                ident=self.create_saved(db,collection,validate(payload['config']))
            else:
                ident=payload.get('id')
                if action=='reset': self.reset_saved(db,collection,ident)
                elif action=='favourite':
                    if not isinstance(payload.get('value'),bool): raise ValueError('Expected favourite boolean')
                    if db.execute('UPDATE saved SET favourite=? WHERE collection=? AND id=?',
                                  (int(payload['value']),collection,ident)).rowcount!=1: raise KeyError('Unknown GIF')
                else: raise ValueError('Unknown action')
            row=db.execute('SELECT * FROM saved WHERE collection=? AND id=?',(collection,ident)).fetchone()
            result=self.item(row)
            db.execute('INSERT INTO api_ops VALUES(?,?,?)',(collection,key,json.dumps(result)))
            return result
