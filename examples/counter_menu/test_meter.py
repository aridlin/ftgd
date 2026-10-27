from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import json
import unittest
from PIL import Image, ImageChops
from server import Store, DEFAULTS, validate, handler_for
from meter import DEFAULTS as METER, STYLES
from render import render_counter


class MeterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'db','http://127.0.0.1')
        self.collection=self.store.new_collection()

    def tearDown(self): self.tmp.cleanup()

    def create(self, **changes):
        return self.store.api_action(self.collection,dict(action='create',key='meter-create',config=dict(METER,**changes)))

    def test_validation_range_signed_decimals_and_limits(self):
        c=validate(dict(METER,minimum='-20',maximum='20',value='-2.500',unit='°C'))
        self.assertEqual(c['value'],'-2.5')
        for changes in (dict(minimum='100'),dict(maximum='0'),dict(value='101'),dict(value='-1'),
                        dict(value='NaN'),dict(value='1e4'),dict(value='0.1234567'),
                        dict(value='9'*13),dict(meter_style='invalid'),dict(mode='counting'),
                        dict(unit='x'*17),dict(unit='\n')):
            with self.subTest(changes=changes),self.assertRaises(ValueError): validate(dict(METER,**changes))
        for value in ('0','100','0.000001'):
            self.assertEqual(validate(dict(METER,value=value))['value'],value)

    def test_all_styles_animate_without_changing_reading(self):
        for style in STYLES:
            for value in ('0','50','100'):
                gif=render_counter(dict(METER,meter_style=style,value=value),animated=True)
                im=Image.open(BytesIO(gif))
                self.assertEqual(im.size,(1200,720));self.assertEqual(im.n_frames,8)
                self.assertLess(len(gif),150000)
                first=im.convert('RGB');im.seek(4);last=im.convert('RGB')
                self.assertIsNone(ImageChops.difference(first.crop((100,175,650,665)),last.crop((100,175,650,665))).getbbox())
                self.assertIsNotNone(ImageChops.difference(first,last).getbbox())

    def test_url_reading_isolated_from_template_seed_and_restart(self):
        item=self.create()
        base='/count/m/'+item['id']
        first=self.store.get(base+'/25/fresh.gif')
        self.assertNotEqual(first,self.store.get(base+'/90/fresh.gif'))
        self.assertEqual(first,self.store.get(base+'/25/fresh.gif'))
        self.assertEqual(first,self.store.get(base+'/25/another.gif'))
        restarted=Store(self.store.path,self.store.base_url)
        self.assertEqual(first,restarted.get(base+'/25.00/fresh.gif'))
        saved=restarted.api_get(self.collection)['items'][0]
        self.assertEqual(saved['config']['value'],'75')
        self.assertIn('/75/',saved['gif']);self.assertIn('/{value}/',saved['gif_template'])
        for value in ('101','-1','nan','1e2','%2F',''):
            with self.subTest(value=value),self.assertRaises(ValueError):self.store.get(base+'/'+value+'/fresh.gif')
        with self.assertRaises(ValueError):self.store.api_action(self.collection,dict(action='reset',key='meter-reset',id=item['id']))

    def test_meter_cache_is_bounded_and_includes_value(self):
        item=self.create()
        with patch('live.render_counter',return_value=b'GIF-test'):
            for value in range(70):self.store.get('/count/m/'+item['id']+'/'+str(value)+'/fresh.gif')
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM snapshots WHERE token LIKE 'meter:%'").fetchone()[0],64)
            self.assertEqual(json.loads(db.execute('SELECT config FROM saved').fetchone()[0])['value'],'75')

    def test_gif_menu_create_customise_save_favourite_and_raw(self):
        url=self.store.url(self.collection)
        def follow(label):
            nonlocal url
            self.store.get(url)
            token=url.rsplit('/',1)[1][:-4]
            with self.store.connect() as db:
                row=db.execute('SELECT * FROM pages_live WHERE collection=? AND id=?',(self.collection,token)).fetchone()
                lines=self.store.menu(db,self.collection,token,row['screen'],json.loads(row['config']),json.loads(row['action']))
            command=next(t.split('  ')[0] for k,t in lines if k=='T' and t.endswith('  '+label))
            _,old,new=command.split('/')
            url=url.replace(old,new,1)
            self.store.get(url)
        follow('METER MODULE')
        follow('RULER')
        for field,value in [('subject','bread_meter'),('minimum','-10'),('value','-2.5'),('unit','points')]:
            url=url.replace('~','-~.'+field+'='+value,1);self.store.get(url)
        follow('NEXT: NOTES');follow('NEXT: PREVIEW AND SAVE');follow('CREATE AND SAVE GIF')
        follow('ADD TO FAVOURITES')
        item=self.store.api_get(self.collection,'bread',True)['items'][0]
        self.assertEqual(item['config']['value'],'-2.5');self.assertEqual(item['config']['subject'],'bread meter')
        self.assertEqual(item['config']['meter_style'],'ruler')
        follow('SHOW THE GIF')
        self.assertEqual(self.store.get(url),self.store.get(item['gif']))

    def test_http_raw_meter_is_gif_for_browsers_and_discord(self):
        item=self.create()
        counter=self.store.api_action(self.collection,dict(action='create',key='counter-create',config=DEFAULTS))
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store))
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        origin='http://127.0.0.1:'+str(server.server_port)
        try:
            for agent in ('Mozilla/5.0','Discordbot/2.0'):
                with urlopen(Request(origin+'/count/m/'+item['id']+'/20/fresh.gif',headers={'Accept':'text/html','User-Agent':agent})) as r:
                    self.assertEqual(r.headers['Content-Type'],'image/gif')
                    self.assertEqual(Image.open(BytesIO(r.read())).n_frames,8)
            for path,code in [('/count/m/'+item['id']+'/101/fresh.gif',400),
                              ('/count/m/'+counter['id']+'/20/fresh.gif',404),
                              ('/count/m/'+item['id']+'/20/fresh.png',404)]:
                with self.assertRaises(HTTPError) as error:urlopen(origin+path)
                self.assertEqual(error.exception.code,code)
                error.exception.close()
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
