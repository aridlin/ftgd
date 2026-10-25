from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
import json
import unittest
from PIL import Image,ImageChops
from server import Store,DEFAULTS,handler_for
from live import current_config
from render import render_counter

class LiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.now=1000.
        self.store=Store(Path(self.tmp.name)/'db','http://127.0.0.1',clock=lambda:self.now)
        self.collection=self.store.new_collection()
    def tearDown(self): self.tmp.cleanup()
    def create(self,mode='counting',unit='hours',value='2'):
        return self.store.api_action(self.collection,dict(action='create',key='create-'+mode+unit+value,
            config=dict(DEFAULTS,mode=mode,unit=unit,value=value)))
    def row(self,ident):
        with self.store.connect() as db:return db.execute('SELECT * FROM saved WHERE id=?',(ident,)).fetchone()

    def test_elapsed_offset_and_reset_without_offset(self):
        for unit,seconds in [('hours',3600),('days',86400)]:
            item=self.create(unit=unit)
            self.now+=seconds*1.5
            self.assertEqual(current_config(self.row(item['id']),self.now)['value'],'3.5')
            self.store.api_action(self.collection,dict(action='reset',id=item['id'],key='reset-'+unit))
            self.assertEqual(current_config(self.row(item['id']),self.now)['value'],'0')
            self.now+=seconds
            self.assertEqual(current_config(self.row(item['id']),self.now)['value'],'1')
            self.store.api_action(self.collection,dict(action='reset',id=item['id'],key='reset-'+unit))
            self.assertEqual(current_config(self.row(item['id']),self.now)['value'],'1')

    def test_static_number_and_animation(self):
        item=self.create('static')
        self.now+=864000
        self.assertEqual(current_config(self.row(item['id']),self.now)['value'],'2')
        gif=self.store.get('/count/g/'+item['id']+'.gif')
        im=Image.open(BytesIO(gif));self.assertEqual(im.n_frames,12)
        first=im.convert('RGB');im.seek(5);last=im.convert('RGB')
        self.assertIsNotNone(ImageChops.difference(first.crop((420,513,553,646)),last.crop((420,513,553,646))).getbbox())
        self.assertIsNotNone(ImageChops.difference(first.crop((40,80,125,170)),last.crop((40,80,125,170))).getbbox())
        self.assertIsNone(ImageChops.difference(first.crop((100,260,410,500)),last.crop((100,260,410,500))).getbbox())

    def test_seed_refresh_does_not_reset_and_same_seed_stable(self):
        item=self.create()
        path='/count/g/'+item['id']+'/one.gif'
        first=self.store.get(path)
        self.now+=3600
        self.assertEqual(first,self.store.get(path))
        self.assertNotEqual(first,self.store.get(path.replace('one','two')))
        self.assertEqual(self.row(item['id'])['started'],1000)
        root=self.store.url(self.collection,seed='hello world / ~')
        self.assertIn('/v2/hello%20world%20%2F%20%7E/',root)
        self.assertTrue(self.store.get(root).startswith(b'GIF'))

    def test_menu_reset_runs_once_across_seeds_and_ownership(self):
        item=self.create();self.now=2000
        with self.store.connect() as db:
            token=self.store.node(db,self.collection,'saved',DEFAULTS,{'kind':'reset','id':item['id']})
        self.store.page(self.collection,token,'first')
        self.now=5600
        self.store.page(self.collection,token,'second')
        self.assertEqual(self.row(item['id'])['started'],2000)
        other=self.store.new_collection()
        with self.assertRaises(KeyError):
            self.store.api_action(other,dict(action='reset',id=item['id'],key='wrong-reset'))
        again=Store(self.store.path,self.store.base_url,clock=lambda:self.now)
        self.assertEqual(again.api_get(self.collection)['items'][0]['config']['value'],'1')

    def test_legacy_saved_gif_is_unchanged(self):
        old=dict(DEFAULTS);del old['mode'];del old['subject']
        gif=render_counter(old)
        with self.store.connect() as db:
            db.execute('INSERT INTO saved(id,collection,config,gif) VALUES(?,?,?,?)',
                       ('f'*32,self.collection,json.dumps(old),gif))
        self.assertEqual(self.store.get('/count/g/'+'f'*32+'.gif'),gif)
        item=self.store.api_get(self.collection)['items'][0]
        self.assertEqual(item['config']['subject'],'kiko shat himself')
        self.assertEqual(item['config']['mode'],'static')

    def test_new_seed_library_choices_do_not_reuse_other_items(self):
        first=self.create('static',value='1')
        with self.store.connect() as db:
            token=self.store.node(db,self.collection,'library',DEFAULTS)
        self.store.page(self.collection,token,'old')
        second=self.create('static',value='2')
        self.store.page(self.collection,token,'new')
        with self.store.connect() as db:
            actions=[json.loads(r['action']) for r in db.execute('SELECT action FROM pages_live WHERE collection=? AND screen=?',
                       (self.collection,'saved'))]
        ids={a['id'] for a in actions if a and a['kind']=='view'}
        self.assertIn(first['id'],ids);self.assertIn(second['id'],ids)

    def test_browser_html_discord_gif_and_api(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store))
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        path=self.store.url(self.collection).replace(self.store.base_url,base)
        try:
            for headers,kind in [({'Accept':'text/html','User-Agent':'Mozilla/5.0'},'text/html'),
                                 ({'Accept':'text/html','User-Agent':'Discordbot/2.0'},'image/gif'),
                                 ({'Accept':'image/*','User-Agent':'Mozilla/5.0'},'image/gif')]:
                with urlopen(Request(path,headers=headers)) as response:
                    self.assertIn(kind,response.headers['Content-Type'])
                    self.assertIn('Accept',response.headers['Vary'])
                    body=response.read()
                    self.assertTrue(b'Counter studio' in body if kind=='text/html' else body.startswith(b'GIF'))
            with urlopen(Request(path+'?format=gif',headers={'Accept':'text/html'})) as response:
                self.assertEqual(response.headers['Content-Type'],'image/gif')
            req=Request(base+'/count/api/'+self.collection,data=json.dumps(dict(action='create',key='http-create',config=dict(DEFAULTS,mode='static'))).encode(),headers={'Content-Type':'application/json'})
            with urlopen(req) as response:self.assertIn('id',json.load(response))
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
