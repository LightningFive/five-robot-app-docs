"""Verify/read a bounded public theme context; standard library, no network/device/model calls."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check():
    index = json.loads((ROOT/'docs/themes/index.json').read_text(encoding='utf-8'))
    if index.get('schema') != 'x622-theme-context/v1':
        raise ValueError('Unknown theme context index')
    for name, entry in index['files'].items():
        path = (ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Missing/invalid indexed file: '+name)
        data = path.read_bytes()
        if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Theme context differs from selected revision: '+name)
    return index


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--topics', help='development,format,acceptance; return only selected document text')
    a = p.parse_args()
    try:
        index = check()
        if a.topics:
            for topic in dict.fromkeys(a.topics.split(',')):
                if topic not in index['topics']:
                    raise ValueError('Unknown theme topic: '+topic)
                path = index['topics'][topic]
                print('\n--- '+path+' ---\n'+(ROOT/path).read_text(encoding='utf-8'))
        else:
            print(json.dumps({'docs_revision':index['docs_revision'], 'files_checked':len(index['files']),
                'checksums_valid':True, 'topics':index['topics'], 'device_operations':False,
                'network_requests':0, 'model_calls':0}, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit('Theme context failed: '+str(error))
