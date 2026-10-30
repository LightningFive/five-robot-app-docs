"""STY2/FNT2 data compiler and independent validator; no device I/O."""
from __future__ import annotations

import struct

STYLE_HEADER = struct.Struct('<I4HB3s')
STYLE = struct.Struct('<HBBI4h3I2Hh6B')
PAGE = struct.Struct('<2H40h')
FONT_HEADER = struct.Struct('<I4HhH2I')
GLYPH = struct.Struct('<IIHBBhh')
COMPONENTS = ('List', 'Row', 'RowTitle', 'RowValue', 'RowIcon', 'RowArrow', 'Header',
              'Hero', 'Body', 'Note', 'Footer', 'Date', 'Key', 'Password',
              'ProgressTrack', 'ProgressFill', 'Back', 'Page')
STATES = ('Normal', 'Focused', 'Editing', 'Disabled')
FONT_ROLES = ('Title', 'Value', 'Header', 'Body', 'Hero', 'Date', 'Keyboard', 'Status')
PAGES = ('Boot', 'Welcome', 'Menu', 'Apps', 'Settings', 'Wireless', 'System',
         'Diagnostics', 'DiagnosticLive', 'DiagnosticIo', 'DiagnosticDisplay',
         'DiagnosticAudio', 'DiagnosticServices', 'DiagnosticStorage', 'Wifi',
         'WifiNetworks', 'WifiKeyboard', 'WifiPortal', 'Bluetooth', 'InstallMethods',
         'Experimental', 'Installer', 'LanguageSelect', 'ThemeSelect', 'WifiConnecting',
         'WifiFailed', 'Screensaver', 'InstallAP', 'InstallLAN', 'InstallUSB',
         'InstallSuccess', 'PowerOff', 'ThemeRecovery', 'SoftwareUpdate', 'OnlineCatalog',
         'OnlineInstall', 'AppUninstall', 'AppRemoveConfirm', 'AppsEmpty',
         'ThemeInstallMethods', 'ThemeInstallAP', 'ThemeInstallLAN', 'ThemeInstallUSB', 'ThemeInstallSuccess')
SLOTS = ('Content', 'Title', 'Art', 'Hero', 'Detail', 'Note', 'Footer', 'Clock', 'Minutes', 'Date')
FIELDS = ('rect', 'background', 'border', 'text', 'image', 'font', 'radius',
          'border_width', 'opacity', 'align', 'spacing', 'slice')


def verify_presentation(data: bytes) -> list[tuple]:
    if not STYLE_HEADER.size <= len(data) <= 4096:
        raise ValueError('STY2 size outside bound')
    magic, version, size, styles, pages, easing, reserved = STYLE_HEADER.unpack_from(data)
    if (magic, version, size) != (0x32595453, 1, len(data)) or styles > 64 or pages > 12 or easing > 2 or any(reserved):
        raise ValueError('unsupported STY2 header/count/easing')
    if STYLE_HEADER.size + styles * STYLE.size + pages * PAGE.size != len(data):
        raise ValueError('STY2 extent mismatch')
    result, keys = [], set()
    for i in range(styles):
        s = STYLE.unpack_from(data, STYLE_HEADER.size + i * STYLE.size)
        page, component, state, fields, x, y, w, h, bg, border, text, image, font, spacing, radius, bw, opa, align, slice_px, zero = s
        if (page != 0xffff and not 0 < page < len(PAGES)) or component >= len(COMPONENTS) or state >= len(STATES):
            raise ValueError('invalid STY2 selector or immutable boot')
        if not fields or fields & ~4095 or zero or max(bg, border, text) > 0xffffff or radius > 120 or bw > 4 or align > 2 or slice_px > 24 or not -8 <= spacing <= 16:
            raise ValueError('invalid STY2 style')
        if state and fields & 33:
            raise ValueError('STY2 geometry/font must stay constant across visual states')
        if fields & 1 and component in (12,15,17):
            raise ValueError('key grid and live progress width are owned by system controls')
        if fields & 1 and not (-240 <= x <= 240 and -240 <= y <= 240 and 1 <= w <= 240 and 1 <= h <= 240):
            raise ValueError('invalid STY2 geometry')
        if fields & 1 and component == 1 and not 30 <= h <= 60:
            raise ValueError('STY2 row height outside bound')
        if fields & 1 and component == 0 and (x < 0 or y < 0 or x + w > 240 or y + h > 240):
            raise ValueError('STY2 viewport offscreen')
        if fields & 16 and (not image or image == 0x200):
            raise ValueError('invalid STY2 image/immutable brand')
        if fields & 32 and not 0x900 <= font < 0x908:
            raise ValueError('invalid STY2 font role')
        key = page, component, state
        if key in keys:
            raise ValueError('duplicate STY2 selector')
        keys.add(key)
        result.append(s)
    keys.clear()
    for i in range(pages):
        page, slots, *rects = PAGE.unpack_from(data, STYLE_HEADER.size + styles * STYLE.size + i * PAGE.size)
        if not 0 < page < len(PAGES) or not slots or slots >> 10 or page in keys:
            raise ValueError('invalid STY2 page selector')
        keys.add(page)
        for slot in range(10):
            x, y, w, h = rects[slot * 4:slot * 4 + 4]
            if not slots & (1 << slot):
                if x or y or w or h:
                    raise ValueError('inactive STY2 page slot must be zero')
            elif not (-240 <= x <= 240 and -240 <= y <= 240 and 0 <= w <= 240 and 0 <= h <= 240) or bool(w) != bool(h):
                raise ValueError('invalid STY2 page rectangle')
    return result


def verify_font(data: bytes) -> None:
    if not FONT_HEADER.size <= len(data) <= 256 * 1024:
        raise ValueError('invalid FNT2 resource size')
    magic, version, size, count, height, baseline, reserved, bitmap, total = FONT_HEADER.unpack_from(data)
    if (magic, version, size, total) != (0x32544e46, 1, FONT_HEADER.size, len(data)) or not 1 <= count <= 1024 or not 8 <= height <= 64 or not 0 <= baseline <= height or reserved or bitmap != size + count * GLYPH.size or bitmap > total:
        raise ValueError('invalid FNT2 header')
    previous, cursor = 0, bitmap
    for i in range(count):
        code, offset, advance, w, h, x, y = GLYPH.unpack_from(data, size + i * GLYPH.size)
        length = (w * h + 1) // 2
        if not 0x20 <= code <= 0x10ffff or code == 0x7f or 0xd800 <= code <= 0xdfff or code <= previous or offset != cursor or advance > 96 or w > 64 or h > 64 or not -64 <= x <= 64 or not -64 <= y <= 64 or length > total - offset:
            raise ValueError('invalid FNT2 glyph/index/extent')
        cursor += length
        previous = code
    if cursor != total:
        raise ValueError('FNT2 trailing/unindexed bytes')


def compile_presentation(spec: dict) -> bytes:
    """Strict authoring schema. Unknown fields fail rather than silently disappear."""
    if set(spec) - {'schema', 'easing', 'styles', 'pages'} or spec.get('schema') != 1:
        raise ValueError('expected STY2 authoring schema 1')
    records = []
    def color(value):
        return int(value.removeprefix('#'), 16) if isinstance(value, str) else value
    for item in spec.get('styles', []):
        if set(item) - {'page', 'component', 'state', *FIELDS}:
            raise ValueError('unknown style field')
        page = 0xffff if item.get('page', '*') == '*' else PAGES.index(item['page'])
        fields = sum(1 << i for i, key in enumerate(FIELDS) if key in item)
        font = item.get('font', 0)
        if isinstance(font, str):
            font = 0x900 + FONT_ROLES.index(font)
        records.append(STYLE.pack(page, COMPONENTS.index(item['component']),
            STATES.index(item.get('state', 'Normal')), fields, *item.get('rect', (0, 0, 0, 0)),
            color(item.get('background', 0)), color(item.get('border', 0)), color(item.get('text', 0)),
            item.get('image', 0), font, item.get('spacing', 0), item.get('radius', 0),
            item.get('border_width', 0), item.get('opacity', 0), item.get('align', 0), item.get('slice', 0), 0))
    pages = []
    for name, slots in spec.get('pages', {}).items():
        if set(slots) - set(SLOTS):
            raise ValueError('unknown page slot')
        mask = sum(1 << SLOTS.index(key) for key in slots)
        rects = [v for key in SLOTS for v in slots.get(key, (0, 0, 0, 0))]
        pages.append(PAGE.pack(PAGES.index(name), mask, *rects))
    body = b''.join(records + pages)
    data = STYLE_HEADER.pack(0x32595453, 1, STYLE_HEADER.size + len(body), len(records), len(pages),
        ('linear', 'ease-in-out', 'ease-out').index(spec.get('easing', 'ease-out')), b'\0' * 3) + body
    verify_presentation(data)
    return data
