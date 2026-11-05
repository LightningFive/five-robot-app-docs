import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from test_tools import module

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from generate_api import generate,minimum_minor
from workflow_context import context
from xapp import xapp_tool

class Api217(unittest.TestCase):
    def test_new_import_gates_and_old_contracts(self):
        names={'ws_open_ex','ws_status_ex','http_request_headers','http_release',
               'opus_start','opus_submit','opus_read','opus_status','opus_stop'}
        index={f['name']:f for f in generate()['functions']}
        for name in names:self.assertEqual(index[name]['minimum_api'],'2.17')
        for name in ('ws_open','ws_send','clock_utc','ble_open'):
            self.assertEqual(minimum_minor(name),16)

    def test_old_descriptor_rejects_new_import(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);w=p/'app.wasm';w.write_bytes(module(imported='http_release'))
            resources=p/'resources';resources.mkdir();manifest=p/'app.json'
            for minor in (16,17):
                manifest.write_text(json.dumps(dict(id='header-test',name='Test',version='1',
                                                   api_minor=minor,permissions=96)),encoding='utf-8')
                args=SimpleNamespace(manifest=manifest,wasm=w,resources=resources,output=p/'test.xapp')
                if minor==16:
                    with self.assertRaisesRegex(ValueError,'API 2.17'):xapp_tool.command_pack(args)
                else:
                    xapp_tool.command_pack(args)
                    self.assertIn('http_release',xapp_tool.verify_bytes(args.output.read_bytes())['profile']['imports'])

    def test_voice_context_has_real_headers_and_startup_order(self):
        text,metadata=context(['opus','net','http'])
        for header in ('x622_opus.h','x622_net_ex.h','x622_http_headers.h'):
            self.assertIn(header,metadata['headers'])
        self.assertIn('explicit wifi_start',text)
        self.assertIn('x622_opus_submit',text)
        self.assertIn('x622_ws_open_ex',text)
        self.assertIn('2.17',text)
