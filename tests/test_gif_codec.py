"""Decode the public image encoder with an independent GIF decoder."""
from io import BytesIO
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

class CodecTests(unittest.TestCase):
    def encode(self, image):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'input.ppm'
            image.save(path)
            return subprocess.check_output([str(ROOT/'build/counter-menu'), str(path)])

    def test_dictionary_growth_resets_and_exact_pixels(self):
        rng = random.Random(74921)
        palette = [(r,g,b) for r in range(0,256,51) for g in range(0,256,51) for b in range(0,256,51)]
        for size in ((1,1), (2,1), (253,1), (255,1), (512,1), (257,257)):
            im=Image.new('RGB',size)
            im.putdata([rng.choice(palette) for _ in range(size[0]*size[1])])
            data=self.encode(im)
            with Image.open(BytesIO(data)) as decoded:
                decoded.load()
                self.assertEqual(decoded.convert('RGB').tobytes(),im.tobytes())

    def test_repeating_patterns_compress_and_decode(self):
        im=Image.new('RGB',(1000,700),(51,102,153))
        data=self.encode(im)
        self.assertLess(len(data),3000)
        with Image.open(BytesIO(data)) as decoded:
            self.assertEqual(decoded.convert('RGB').tobytes(),im.tobytes())

    def test_animated_dashboard_frames_decode(self):
        with Image.open(ROOT/'build/basic.gif') as im:
            self.assertGreater(im.n_frames,1)
            for index in range(im.n_frames):
                im.seek(index)
                im.load()

if __name__=='__main__':
    unittest.main()
