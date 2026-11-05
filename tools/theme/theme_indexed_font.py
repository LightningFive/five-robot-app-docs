"""FNT3: bounded, independently compressed A4 glyphs for theme ABI 4.

This format never applies to the existing XApp FNT2 API. Decoder scratch is
516 bytes and decoded glyphs remain <=512 bytes. Fonts stay on Flash.
"""
import struct
from theme_presentation import FONT_HEADER, GLYPH

PACKED_GLYPH = struct.Struct('<IIHBBhhHH')
MAGIC = 0x33544e46


def encode(raw):
    result = bytearray()
    at = 0
    while at < len(raw):
        run = 1
        while run < 128 and at + run < len(raw) and raw[at + run] == raw[at]:
            run += 1
        if run >= 3:
            result.extend((0x80 | (run - 1), raw[at])); at += run
            continue
        start = at
        while at < len(raw) and at - start < 128:
            if at + 2 < len(raw) and raw[at] == raw[at + 1] == raw[at + 2]:
                break
            at += 1
        result.append(at - start - 1); result += raw[start:at]
    return (1, bytes(result)) if len(result) < len(raw) else (0, bytes(raw))


def decode(data, codec, size):
    if size > 512 or len(data) > 516 or codec not in (0, 1):
        raise ValueError('FNT3 glyph budget')
    if codec == 0:
        if len(data) != size: raise ValueError('FNT3 raw extent')
        return bytes(data)
    out = bytearray(); at = 0
    while at < len(data):
        control = data[at]; at += 1
        n = (control & 127) + 1; stored = 1 if control & 128 else n
        if n > size - len(out) or stored > len(data) - at:
            raise ValueError('FNT3 run extent')
        out += bytes([data[at]]) * n if control & 128 else data[at:at+n]
        at += stored
    if len(out) != size: raise ValueError('FNT3 decoded extent')
    return bytes(out)


def verify_indexed_font(data):
    if not 24 <= len(data) <= 2 * 1024 * 1024: raise ValueError('FNT3 size')
    magic, version, head, count, height, baseline, reserved, bitmap, total = FONT_HEADER.unpack_from(data)
    if (magic, version, head, total) != (MAGIC, 1, 24, len(data)) or not 1 <= count <= 24576 or not 8 <= height <= 64 or not 0 <= baseline <= height or reserved or bitmap != 24 + count * 20 or bitmap > total:
        raise ValueError('FNT3 header')
    previous, cursor = 0, bitmap
    for i in range(count):
        code, at, advance, w, h, x, y, stored, codec = PACKED_GLYPH.unpack_from(data, 24 + i * 20)
        if not 32 <= code <= 0x10ffff or code == 127 or 0xd800 <= code <= 0xdfff or code <= previous or at != cursor or advance > 96 or w > 64 or h > 64 or not -64 <= x <= 64 or not -64 <= y <= 64 or stored > total - at or (codec == 1 and (not stored or not w * h)):
            raise ValueError('FNT3 index/metrics')
        decode(data[at:at+stored], codec, (w * h + 1) // 2)
        cursor += stored; previous = code
    if cursor != total: raise ValueError('FNT3 trailing bytes')


def extend_font(original, source, size, characters):
    """Keep every original metric/bitmap; only insert missing source glyphs."""
    from PIL import ImageFont
    from fontTools.ttLib import TTFont
    from theme_presentation import verify_font
    verify_font(original)
    header = list(FONT_HEADER.unpack_from(original))
    glyphs = {}
    for i in range(header[3]):
        g = GLYPH.unpack_from(original, 24 + i * 16)
        glyphs[g[0]] = (g, original[g[1]:g[1] + (g[3] * g[4] + 1) // 2])
    with TTFont(source) as face: available = face.getBestCmap()
    missing = sorted(set(map(ord, characters)) - glyphs.keys())
    if any(cp not in available for cp in missing): raise ValueError('source lacks requested glyphs')
    font = ImageFont.truetype(str(source), size)
    for cp in missing:
        mask, (x, top) = font.getmask2(chr(cp), mode='L', anchor='ls')
        w, h = mask.size
        raw = bytes(mask); pixels = bytearray()
        for i in range(0, len(raw), 2):
            high = (raw[i] * 15 + 127) // 255
            low = (raw[i + 1] * 15 + 127) // 255 if i + 1 < len(raw) else 0
            pixels.append(high << 4 | low)
        glyphs[cp] = ((cp, 0, round(font.getlength(chr(cp))), w, h, x, -(top + h)), bytes(pixels))
    index, pixels = bytearray(), bytearray(); base = 24 + len(glyphs) * 20
    for cp in sorted(glyphs):
        g, raw = glyphs[cp]; codec, packed = encode(raw)
        index += PACKED_GLYPH.pack(cp, base + len(pixels), *g[2:], len(packed), codec)
        pixels += packed
    header[0], header[3], header[7], header[8] = MAGIC, len(glyphs), base, base + len(pixels)
    result = FONT_HEADER.pack(*header) + index + pixels
    verify_indexed_font(result)
    return bytes(result)
