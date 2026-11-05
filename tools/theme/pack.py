"""Build a data-only .xtheme with the production format validators; no device I/O."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import zlib

from layout_codec import pack_layout
from theme_presentation import compile_presentation
from theme_tool import HEADER, ENTRY, MAX_THEME_PACKAGE, verify_layout, verify_theme_bytes

KINDS = {'A8': 1, 'RGB565A8': 2, 'RGB565': 3, 'Font': 5}


def source(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('Resource path must be relative to the project')
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Resource missing or outside project: ' + value)
    if path.stat().st_size > MAX_THEME_PACKAGE:
        raise ValueError('Source file exceeds theme limit')
    return path


def integer(value):
    if type(value) is int:
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError('Expected integer or 0x-prefixed resource ID')


def field(value: str, capacity: int) -> bytes:
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Empty or invalid package text')
    encoded = value.encode('utf-8')
    if len(encoded) >= capacity:
        raise ValueError('UTF-8 text exceeds package field')
    return encoded


def bitmap(path, kind, width, height):
    if path.stat().st_size > MAX_THEME_PACKAGE:
        raise ValueError('Source resource exceeds package limit')
    if path.suffix.lower() != '.png':
        return path.read_bytes(), integer(width), integer(height)
    from PIL import Image
    with Image.open(path) as image:
        if not 0 < image.width <= 240 or not 0 < image.height <= 240:
            raise ValueError('PNG exceeds native 240x240 bounds')
        image = image.convert('RGBA')
        w, h = image.size
        if width is not None and integer(width) != w or height is not None and integer(height) != h:
            raise ValueError('PNG geometry differs from manifest')
        if kind == 1:
            return image.getchannel('A').tobytes(), w, h
        out = bytearray()
        for red, green, blue, alpha in struct.iter_unpack('4B', image.tobytes()):
            if kind == 3 and alpha != 255:
                raise ValueError('RGB565 cannot silently discard transparency; use RGB565A8')
            pixel = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
            out += struct.pack('<H', pixel)
            if kind == 2:
                out.append(alpha)
        return bytes(out), w, h


def build(manifest: Path, output: Path) -> dict:
    manifest = manifest.resolve()
    root = manifest.parent
    spec = json.loads(manifest.read_text(encoding='utf-8'))
    allowed = {'schema', 'id', 'name', 'version', 'engine_abi', 'appearances', 'layout',
               'resources', 'presentation', 'native_scene', 'notes'}
    if set(spec) - allowed or spec.get('schema') != 'x622-theme-project/v1':
        raise ValueError('Unknown field or unsupported project schema')
    identity = spec['id']
    if not isinstance(identity, str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,30}', identity):
        raise ValueError('Theme ID must be 1..31 lowercase ASCII letters/digits/_/-')
    abi, appearances = integer(spec['engine_abi']), integer(spec['appearances'])
    if abi not in (1, 2, 3, 4, 5) or appearances not in (1, 2, 3):
        raise ValueError('Unsupported engine ABI or appearance mask')
    name, version = field(spec['name'], 48), field(spec['version'], 16)
    if not isinstance(spec.get('resources', []), list) or len(spec.get('resources', [])) > 256 - (2 if abi in (2, 5) else 1):
        raise ValueError('Resource list exceeds package bound')
    layout_spec = json.loads(source(root, spec['layout']).read_text(encoding='utf-8'))
    layout = pack_layout(layout_spec)
    verify_layout(layout)
    records = [(1, 4, 0, 0, 0, layout)]
    if abi in (3, 4):
        if spec.get('resources') or spec.get('presentation'):
            raise ValueError('ABI3/4 contains only layout and an already compiled NSC1 scene')
        records.append((3, 7, 0, 0, 0, source(root, spec['native_scene']).read_bytes()))
    else:
        if 'native_scene' in spec or abi == 1 and 'presentation' in spec:
            raise ValueError('Extension not supported by selected ABI')
        if abi in (2, 5):
            presentation = json.loads(source(root, spec['presentation']).read_text(encoding='utf-8'))
            records.append((2, 6, 0, 0, 0, compile_presentation(presentation)))
        for entry in spec.get('resources', []):
            if set(entry) - {'id', 'format', 'path', 'width', 'height', 'flags'}:
                raise ValueError('Unknown resource field')
            key, kind = integer(entry['id']), KINDS[entry['format']]
            flags = integer(entry.get('flags', 0))
            path = source(root, entry['path'])
            if kind == 5:
                if abi not in (2, 5) or not 0x900 <= key < 0x908 or flags:
                    raise ValueError('Fonts require ABI2/5 role 0x900..0x907 and shared appearance')
                data, w, h = path.read_bytes(), 0, 0
            else:
                data, w, h = bitmap(path, kind, entry.get('width'), entry.get('height'))
            records.append((key, kind, flags, w, h, data))
    at = HEADER.size + len(records) * ENTRY.size
    table, payload = bytearray(), bytearray()
    for key, kind, flags, w, h, data in records:
        if at + len(data) > MAX_THEME_PACKAGE:
            raise ValueError('Theme exceeds 4 MiB limit')
        table += ENTRY.pack(key, kind, flags, w, h, at, len(data), zlib.crc32(data), 0, 0)
        payload += data
        at += len(data)
    body = bytes(table + payload)
    header = bytearray(HEADER.pack(b'XTHM', 1, 256, 256 + len(body), abi, 32,
        appearances, 240, 240, 256, len(records), 256 + len(table), len(layout),
        field(identity, 32), name, version, hashlib.sha256(body).digest(), bytes(84), 0))
    struct.pack_into('<I', header, 252, zlib.crc32(header[:252]))
    package = bytes(header) + body
    result = verify_theme_bytes(package)  # Do not publish any bytes until this passes.
    output = output.resolve()
    inputs = {manifest, source(root, spec['layout'])}
    inputs.update(source(root, entry['path']) for entry in spec.get('resources', []))
    inputs.update(source(root, spec[key]) for key in ('presentation', 'native_scene') if key in spec)
    if output in inputs or output.with_suffix('.validation.json') in inputs:
        raise ValueError('Output would overwrite project source')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.theme-', delete=False) as file:
            temporary = Path(file.name)
            file.write(package)
        os.replace(temporary, output)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    result.update(package_sha256=hashlib.sha256(package).hexdigest(), file=output.name,
                  source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                  format_validated=True, visual_verified=False, hardware_tested=False,
                  performance_measured=False)
    output.with_suffix('.validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True, help='Path to theme.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.project, args.output), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, struct.error, ImportError) as error:
        raise SystemExit('Theme build failed: ' + str(error))
