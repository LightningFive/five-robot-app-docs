"""Public theme packaging contract tests; tiny fixtures are not deliverable artwork."""
from pathlib import Path
import copy
import hashlib
import json
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/theme'))
from pack import build
from theme_tool import REQUIRED_IMAGES, verify_theme_bytes
from theme_presentation import FONT_HEADER, GLYPH
from theme_native_scene import HEADER as NH, ASSET, SCENE, NODE
from theme_indexed_font import MAGIC as FNT3_MAGIC, PACKED_GLYPH, encode, decode


class ThemeTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root.joinpath('layout.json').write_bytes((ROOT/'examples/theme-starter/layout.json').read_bytes())
        self.root.joinpath('presentation.json').write_bytes((ROOT/'examples/theme-starter/presentation.json').read_bytes())
        self.root.joinpath('pixel.bin').write_bytes(b'\xff')
        self.spec = {'schema':'x622-theme-project/v1','id':'test-theme','name':'合同夹具',
            'version':'1.0.0','engine_abi':2,'appearances':2,'layout':'layout.json',
            'presentation':'presentation.json','resources':[
                {'id':key,'format':'A8','path':'pixel.bin','width':1,'height':1}
                for key in (*REQUIRED_IMAGES,0x505)]}

    def tearDown(self):
        self.temp.cleanup()

    def pack(self, spec=None):
        manifest = self.root/'theme.json'
        manifest.write_text(json.dumps(spec or self.spec, ensure_ascii=False), encoding='utf8')
        return build(manifest, self.root/'result.xtheme')

    def test_abi1_abi2_and_reproducibility(self):
        first = self.pack()
        self.assertTrue(first['format_validated'])
        self.assertFalse(first['hardware_tested'])
        self.assertFalse(first['visual_verified'])
        self.assertEqual(first, self.pack())
        spec = copy.deepcopy(self.spec)
        spec['engine_abi'] = 1
        del spec['presentation']
        self.assertEqual(self.pack(spec)['engine_abi'], 1)

    def test_full_payload_hash_and_preserve_valid_output(self):
        self.pack()
        original = (self.root/'result.xtheme').read_bytes()
        bad = bytearray(original); bad[-1] ^= 1
        with self.assertRaises(ValueError): verify_theme_bytes(bad)
        spec = copy.deepcopy(self.spec); spec['resources'].pop()
        with self.assertRaises(ValueError): self.pack(spec)
        self.assertEqual(original, (self.root/'result.xtheme').read_bytes())

    def test_brand_collision_duplicate_and_path_escape(self):
        for extra in (
            {'id':0x200,'format':'A8','path':'pixel.bin','width':1,'height':1},
            {'id':0x100,'format':'A8','path':'pixel.bin','width':1,'height':1},
            {'id':0x120,'format':'A8','path':'../outside.bin','width':1,'height':1}):
            spec = copy.deepcopy(self.spec); spec['resources'].append(extra)
            with self.assertRaises(ValueError): self.pack(spec)

    def test_layout_and_appearance_failures(self):
        layout = json.loads((self.root/'layout.json').read_text('utf8'))
        layout['metrics']['TitleFont'] = 24
        (self.root/'layout.json').write_text(json.dumps(layout),encoding='utf8')
        with self.assertRaises(ValueError): self.pack()
        self.root.joinpath('layout.json').write_bytes((ROOT/'examples/theme-starter/layout.json').read_bytes())
        spec = copy.deepcopy(self.spec); spec['appearances']=3
        spec['resources'][0]['flags']=2
        with self.assertRaises(ValueError): self.pack(spec)

    def test_tiny_nsc1_container(self):
        # Parser fixture only: 93 one-node scenes, never advertised as a design.
        font = FONT_HEADER.pack(0x32544e46,1,24,1,8,0,0,40,41) + GLYPH.pack(65,40,6,1,1,0,0) + b'\xf0'
        metadata = struct.pack('<4sHH8I4H',b'NMD1',1,0,*([0]*12))
        assets = [(2,0,0,font),(1,1,1,b'\xff\xff\xff\xff'),(5,0,0,metadata)]
        scenes=93; aa=64; sa=aa+3*32; na=sa+scenes*16; pa=na+scenes*32
        index=bytearray();payload=bytearray();at=pa
        for kind,w,h,data in assets:
            index+=ASSET.pack(kind,w,h,0,at,len(data),zlib.crc32(data),0,0,0)
            payload+=data;at+=len(data)
        header=NH.pack(b'NSC1',1,64,at,3,scenes,aa,sa,na,scenes,pa,1,3,*([0]*8))
        table=b''.join(SCENE.pack(i+1,0,i,1,0) for i in range(scenes))
        nodes=NODE.pack(1,0,1,0,0,1,1,0,0,0,0,0,0)*scenes
        (self.root/'scene.nscene').write_bytes(header+index+table+nodes+payload)
        spec = {k:v for k,v in self.spec.items() if k not in ('resources','presentation')}
        spec.update(engine_abi=3,native_scene='scene.nscene')
        self.assertEqual(self.pack(spec)['engine_abi'],3)

    def test_png_alpha_and_interleaving_when_pillow_available(self):
        try: from PIL import Image
        except ImportError: self.skipTest('Pillow optional PNG branch')
        Image.new('RGBA',(1,1),(255,0,0,128)).save(self.root/'pixel.png')
        spec=copy.deepcopy(self.spec)
        spec['resources'][0].update(path='pixel.png',format='RGB565A8')
        self.pack(spec)
        package=(self.root/'result.xtheme').read_bytes()
        self.assertIn(b'\x00\xf8\x80',package)
        spec['resources'][0]['format']='RGB565'
        with self.assertRaises(ValueError):self.pack(spec)

    def test_classic_indexed_title_font_and_legacy_rejection(self):
        font = FONT_HEADER.pack(FNT3_MAGIC,1,24,1,8,0,0,44,45)
        font += PACKED_GLYPH.pack(65,44,6,1,1,0,0,1,0) + b'\xf0'
        (self.root/'title.fnt3').write_bytes(font)
        spec=copy.deepcopy(self.spec);spec['engine_abi']=5
        spec['resources'].append({'id':0x900,'format':'Font','path':'title.fnt3'})
        self.assertEqual(self.pack(spec)['engine_abi'],5)
        valid=(self.root/'result.xtheme').read_bytes()
        spec['engine_abi']=2
        with self.assertRaises(ValueError):self.pack(spec)
        self.assertEqual((self.root/'result.xtheme').read_bytes(),valid)
        spec['engine_abi']=5
        bad=bytearray(font);struct.pack_into('<H',bad,42,99)
        (self.root/'title.fnt3').write_bytes(bad)
        with self.assertRaises(ValueError):self.pack(spec)
        self.assertEqual((self.root/'result.xtheme').read_bytes(),valid)

    def test_independent_indexed_glyph_boundaries(self):
        for size in (0,1,2,127,128,129,511,512):
            for raw in (bytes(size),bytes(i%251 for i in range(size))):
                codec,packed=encode(raw)
                self.assertEqual(decode(packed,codec,size),raw)
        with self.assertRaises(ValueError):decode(b'\xff',1,1)


if __name__ == '__main__': unittest.main()
