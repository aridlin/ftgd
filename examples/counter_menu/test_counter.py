from io import BytesIO
from pathlib import Path
import json
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from PIL import Image
from server import Store, DEFAULTS, PRESETS, validate
from render import render_counter

class CounterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'data.sqlite3', 'https://example.test')
        self.collection = self.store.new_collection()

    def tearDown(self):
        self.tmp.cleanup()

    def node(self, screen, config=None, action=None):
        with self.store.connect() as db:
            return self.store.node(db, self.collection, screen, config or DEFAULTS, action)

    def saved(self):
        token = self.node('saved', PRESETS['microseconds'], {'kind': 'save'})
        self.store.page(self.collection, token)
        with self.store.connect() as db:
            return token, dict(db.execute('SELECT * FROM saved').fetchone())

    def test_real_renderer_all_screens_and_presets(self):
        for screen in ('settings', 'notes', 'preview', 'library', 'favourites'):
            token = self.node(screen)
            result = self.store.page(self.collection, token)
            image = Image.open(BytesIO(result))
            image.load()
            self.assertEqual(image.width, 1200)
        for config in PRESETS.values():
            image = Image.open(BytesIO(render_counter(config)))
            image.load()
            self.assertEqual(image.size, (1200, 720))
            self.assertEqual(image.n_frames, 1)

    def test_repeated_concurrent_save_is_exactly_once_and_survives_restart(self):
        token = self.node('saved', action={'kind': 'save'})
        with ThreadPoolExecutor(max_workers=4) as pool:
            bodies = list(pool.map(lambda _: self.store.page(self.collection, token), range(4)))
        self.assertTrue(all(body == bodies[0] for body in bodies))
        store = Store(self.store.path, self.store.base_url)
        with store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM saved').fetchone()[0], 1)
            saved = db.execute('SELECT * FROM saved').fetchone()
        self.assertEqual(store.get('/count/g/' + saved['id'] + '.gif'), bytes(saved['gif']))
        self.assertEqual(store.page(self.collection, token), bodies[0])

    def test_favourites_add_remove_ownership_and_raw_navigation(self):
        saved_token, saved = self.saved()
        with self.store.connect() as db:
            raw_token = db.execute("SELECT id FROM pages WHERE collection=? AND screen='raw'", (self.collection,)).fetchone()['id']
        self.assertEqual(self.store.get(self.store.url(self.collection, raw_token)), saved['gif'])
        for value in (True, False):
            token = self.node('saved', action={'kind': 'favourite', 'id': saved['id'], 'value': value})
            self.store.page(self.collection, token)
            with self.store.connect() as db:
                self.assertEqual(db.execute('SELECT favourite FROM saved').fetchone()[0], value)
        self.assertEqual(self.store.get(f'/count/gifmenu/{self.collection}/raw-{saved["id"]}.gif'), saved['gif'])
        other = self.store.new_collection()
        with self.assertRaises(KeyError):
            self.store.get(f'/count/gifmenu/{other}/raw-{saved["id"]}.gif')
        with self.store.connect() as db:
            token = self.store.node(db, other, 'saved', DEFAULTS, {'kind':'favourite', 'id':saved['id'], 'value':True})
        with self.assertRaises(KeyError):
            self.store.page(other, token)

    def test_custom_text_is_literal_validated_and_keeps_navigation(self):
        text = 'hello_world_%26_caf%C3%A9'
        path = f'/count/gifmenu/{self.collection}/~n~{text}~~b.gif'
        self.store.get(path)
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM pages WHERE screen='notes'").fetchall()
        self.assertTrue(all(r['id'].endswith('b') for r in rows))
        self.assertTrue(all(json.loads(r['config'])['note'] == 'hello world & café' for r in rows))
        for value in ('-1', 'NaN', 'inf', '1e99999', '1/2', '1;exit'):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, value=value))
        for text in ('x'*181, 'line\nbreak', 'bad\tfield'):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, note=text))
        self.assertEqual(validate(dict(DEFAULTS, value='1.25'))['value'], '1.25')

    def test_invalid_input_rolls_back_and_old_menu_is_immutable(self):
        original = self.store.page(self.collection, 'b')
        with self.assertRaises(ValueError):
            self.store.page(self.collection, '~v~oops~~b')
        with self.store.connect() as db:
            self.assertFalse(db.execute("SELECT 1 FROM pages WHERE id='~v~oops~~b'").fetchone())
        self.assertEqual(original, self.store.page(self.collection, 'b'))

    def test_library_pagination(self):
        gif = render_counter(DEFAULTS)
        with self.store.connect() as db:
            for index in range(8):
                db.execute('INSERT INTO saved(id,collection,config,gif) VALUES(?,?,?,?)',
                    (f'{index:032x}', self.collection, json.dumps(DEFAULTS), gif))
            first = self.store.menu(db, self.collection, 'b', 'library', DEFAULTS, None)
            second = self.store.menu(db, self.collection, 'b', 'library', DEFAULTS, {'offset':6})
        self.assertIn('NEXT PAGE', str(first))
        self.assertNotIn('NEXT PAGE', str(second))
        self.assertIn('PREVIOUS PAGE', str(second))

    def test_short_commands_work_on_whole_url_with_b_in_internal_id(self):
        collection = 'ab'*16
        with self.store.connect() as db:
            db.execute('INSERT INTO collections VALUES(?)', (collection,))
            self.store.node(db, collection, 'settings', DEFAULTS, ident='b')
        url = self.store.url(collection)
        self.assertEqual(url.count('b'), 1)
        for expected in ('1b', '11b', '111b'):
            self.store.get(url)
            url = url.replace('b', '1b', 1)
            self.assertTrue(url.endswith('/'+expected+'.gif'))
            image = Image.open(BytesIO(self.store.get(url)))
            image.load()
        with self.store.connect() as db:
            lines = self.store.menu(db, collection, 'b', 'settings', DEFAULTS, None)
        for kind, line in lines:
            if kind == 'T' and line.startswith('s/'):
                command = line.split('  ')[0]
                self.assertNotIn('.gif', command)
                self.assertTrue(command.endswith('b'))
                if '~' not in command:
                    self.assertRegex(command, r'^s/b/[1-9ac-z]b$')

    def test_b_in_note_does_not_break_following_commands(self):
        token = '~n~bob_brought_bread~~b'
        self.store.page(self.collection, token)
        with self.store.connect() as db:
            lines = self.store.menu(db, self.collection, token, 'notes', dict(DEFAULTS,note='bob brought bread'), None)
        command = next(line.split('  ')[0] for kind,line in lines if 'NEXT: PREVIEW' in line)
        _, old, new = command.split('/')
        url = self.store.url(self.collection,token)
        target = url.replace(old,new,1)
        self.assertIn('bob_brought_bread',target)
        self.store.get(target)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM pages WHERE collection=? AND id=?',(self.collection,target.rsplit('/',1)[1][:-4])).fetchone()
        self.assertEqual(row['screen'],'preview')
        self.assertEqual(json.loads(row['config'])['note'],'bob brought bread')

    def test_old_collection_keeps_saved_images_and_gains_b_root(self):
        _,saved=self.saved()
        with self.store.connect() as db:
            db.execute("DELETE FROM pages WHERE collection=? AND id='b'",(self.collection,))
            self.store.node(db,self.collection,'settings',DEFAULTS,ident='p')
        migrated=Store(self.store.path,self.store.base_url)
        self.assertTrue(migrated.get(migrated.url(self.collection)).startswith(b'GIF'))
        self.assertEqual(migrated.get('/count/g/'+saved['id']+'.gif'),saved['gif'])

if __name__ == '__main__':
    unittest.main()
