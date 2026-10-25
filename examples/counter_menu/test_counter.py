from io import BytesIO
from pathlib import Path
import json
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlsplit
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
            self.assertEqual(image.width, 1600)
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
            raw_token = db.execute("SELECT id FROM pages_v3 WHERE collection=? AND screen='raw'", (self.collection,)).fetchone()['id']
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
        path = self.store.url(self.collection, f'-~.note={text}')
        self.store.get(path)
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM pages_v3 WHERE screen='notes'").fetchall()
        self.assertTrue(all('-~.note=' in r['id'] for r in rows))
        self.assertTrue(all(json.loads(r['config'])['note'] == 'hello world & café' for r in rows))
        for value in ('-1', 'NaN', 'inf', '1e99999', '1/2', '1;exit'):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, value=value))
        for text in ('x'*181, 'line\nbreak', 'bad\tfield'):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS, note=text))
        self.assertEqual(validate(dict(DEFAULTS, value='1.25'))['value'], '1.25')

    def test_invalid_input_rolls_back_and_old_menu_is_immutable(self):
        original = self.store.page(self.collection, '~')
        with self.assertRaises(ValueError):
            self.store.page(self.collection, '-~.value=oops')
        with self.store.connect() as db:
            self.assertFalse(db.execute("SELECT 1 FROM pages_v3 WHERE id='-~.value=oops'").fetchone())
        self.assertEqual(original, self.store.page(self.collection, '~'))

    def test_library_pagination(self):
        gif = render_counter(DEFAULTS)
        with self.store.connect() as db:
            for index in range(8):
                db.execute('INSERT INTO saved(id,collection,config,gif) VALUES(?,?,?,?)',
                    (f'{index:032x}', self.collection, json.dumps(DEFAULTS), gif))
            first = self.store.menu(db, self.collection, '~', 'library', DEFAULTS, None)
            second = self.store.menu(db, self.collection, '~', 'library', DEFAULTS, {'offset':6})
        self.assertIn('NEXT PAGE', str(first))
        self.assertNotIn('NEXT PAGE', str(second))
        self.assertIn('PREVIOUS PAGE', str(second))

    def test_short_commands_work_on_whole_url_with_b_in_internal_id(self):
        collection = 'ab'*16
        with self.store.connect() as db:
            db.execute('INSERT INTO collections VALUES(?)', (collection,))
            self.store.node(db, collection, 'settings', DEFAULTS, ident='~')
        url = self.store.url(collection)
        self.assertEqual(url.count('~'), 1)
        for expected in ('1~', '11~', '111~'):
            self.store.get(url)
            url = url.replace('~', '1~', 1)
            self.assertTrue(url.endswith('/'+expected+'.gif'))
            image = Image.open(BytesIO(self.store.get(url)))
            image.load()
        with self.store.connect() as db:
            lines = self.store.menu(db, collection, '~', 'settings', DEFAULTS, None)
        for kind, line in lines:
            if kind == 'T' and line.startswith('s/'):
                command = line.split('  ')[0]
                self.assertNotIn('.gif', command)
                if '.=' not in command and '.value=' not in command and '.subject=' not in command:
                    self.assertRegex(command, r'^s/~/[1-9a-z]~$')

    def test_b_in_note_does_not_break_following_commands(self):
        token = '-~.note=bob_brought_bread'
        self.store.page(self.collection, token)
        with self.store.connect() as db:
            lines = self.store.menu(db, self.collection, token, 'notes', dict(DEFAULTS,note='bob brought bread'), None)
        command = next(line.split('  ')[0] for kind,line in lines if 'NEXT: PREVIEW' in line)
        _, old, new = command.split('/')
        url = self.store.url(self.collection,token)
        target = url.replace(old,new,1)
        self.assertEqual(command, 's/~/1~')
        self.assertIn('bob_brought_bread',target)
        self.store.get(target)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM pages_v3 WHERE collection=? AND id=?',(self.collection,target.rsplit('/',1)[1][:-4])).fetchone()
        self.assertEqual(row['screen'],'preview')
        self.assertEqual(json.loads(row['config'])['note'],'bob brought bread')

    def test_multiple_inputs_and_navigation_use_first_tilde(self):
        url = self.store.url(self.collection)
        commands = ['s/~/-~.subject=bob_got_a_kill', 's/~/-~.value=0.5',
                    's/~/b~', 's/~/-~.note=bob_brought_bread',
                    's/~/-~.star=BEST', 's/~/1~', 's/~/1~']
        self.store.get(url)
        for command in commands:
            _,old,new = command.split('/')
            url = url.replace(old,new,1)
            self.store.get(url)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM saved WHERE collection=?',(self.collection,)).fetchone()
        config=json.loads(row['config'])
        self.assertEqual(config['subject'],'bob got a kill')
        self.assertEqual(config['value'],'0.5')
        self.assertEqual(config['note'],'bob brought bread')
        self.assertEqual(config['star'],'BEST')
        # A preset reached after editing must override old input values.
        url=self.store.url(self.collection,'-~.value=0.5')
        self.store.get(url)
        url=url.replace('~','2~',1)
        self.store.get(url)
        with self.store.connect() as db:
            config=json.loads(db.execute('SELECT config FROM pages_v3 WHERE collection=? AND id=?',
                (self.collection,urlsplit(url).path.rsplit('/',1)[1][:-4])).fetchone()[0])
        self.assertEqual(config['value'],'0')
        self.assertEqual(config['unit'],'hours')

    def test_all_letters_and_literal_tildes_are_preserved(self):
        for text,expected in [('babel','babel'), ('tower_of_babel','tower of babel'), ('%7E','~'), ('~a~el','~a~el'), ('abcdefghijklmnopqrstuvwxyz','abcdefghijklmnopqrstuvwxyz')]:
            token='-~.subject='+text
            self.store.get(self.store.url(self.collection,token))
            with self.store.connect() as db:
                config=json.loads(db.execute('SELECT config FROM pages_v3 WHERE collection=? AND id=?',
                    (self.collection,token)).fetchone()[0])
            self.assertEqual(config['subject'],expected)
            self.store.get(self.store.url(self.collection,token).replace('~','b~',1))

    def test_edit_and_navigation_histories_do_not_collide(self):
        for reverse in (False, True):
            collection = self.store.new_collection()
            self.store.page(collection, '~')
            self.store.page(collection, '2~')
            self.store.page(collection, '-~.value=5')
            paths = ['2-~.value=5', '-2~.value=5']
            for token in reversed(paths) if reverse else paths:
                self.store.page(collection, token)
            with self.store.connect() as db:
                for token, expected in zip(paths, ('5', '0')):
                    config = json.loads(db.execute('SELECT config FROM pages_v3 WHERE collection=? AND id=?',
                        (collection, token)).fetchone()[0])
                    self.assertEqual(config['value'], expected)
                    self.assertEqual(config['unit'], 'hours')
            # Revisiting either immutable URL preserves its own state.
            self.assertEqual(self.store.page(collection, paths[0]), self.store.page(collection, paths[0]))

    def test_origin_cannot_contain_navigation_marker(self):
        with self.assertRaisesRegex(ValueError, 'navigation marker'):
            Store(Path(self.tmp.name)/'bad.sqlite3', 'https://example.test/~')
        Store(Path(self.tmp.name)/'blue.sqlite3', 'https://blue.example')

    def test_subject_validation_and_old_configs(self):
        old=dict(DEFAULTS)
        del old['subject']
        self.assertEqual(validate(old)['subject'],DEFAULTS['subject'])
        for subject in ('', ' ', 'x'*81, 'bad\nsubject'):
            with self.assertRaises(ValueError):
                validate(dict(DEFAULTS,subject=subject))
        for subject in ('kill', 'bob got a kill', 'x'*80):
            image=Image.open(BytesIO(render_counter(dict(DEFAULTS,subject=subject))))
            image.load()
            self.assertEqual(image.size,(1200,720))

    def test_old_collection_keeps_saved_images_and_gains_tilde_root(self):
        _,saved=self.saved()
        with self.store.connect() as db:
            db.execute("DELETE FROM pages_v3 WHERE collection=? AND id='~'",(self.collection,))
            self.store.node(db,self.collection,'settings',DEFAULTS,ident='p')
        migrated=Store(self.store.path,self.store.base_url)
        self.assertTrue(migrated.get(migrated.url(self.collection)).startswith(b'GIF'))
        self.assertEqual(migrated.get('/count/g/'+saved['id']+'.gif'),saved['gif'])

if __name__ == '__main__':
    unittest.main()
