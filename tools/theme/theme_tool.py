#!/usr/bin/env python3
"""Verify data-only XTHM ABI 1/2 packages before transport (no device I/O)."""

from __future__ import annotations

import hashlib
import pathlib
import struct
import zlib
from theme_presentation import verify_presentation, verify_font
from theme_native_scene import verify_native_scene

HEADER = struct.Struct("<4sHHIHHIHHIIII32s48s16s32s84sI")
ENTRY = struct.Struct("<IHHHHIII2I")
MAX_THEME_PACKAGE = 4 * 1024 * 1024
MAX_RESOURCES = 256
LAYOUT_BYTES = 2968
REQUIRED_IMAGES = tuple(range(0x100, 0x117)) + tuple(range(0x201, 0x20c)) + \
    tuple(range(0x300, 0x30a)) + (0x400, 0x402, 0x403, 0x500, 0x501, 0x502) + \
    tuple(0x600 + ord(character) for character in "0123456789:-")
HOME_CLOCK_IMAGES = tuple(0x800 + ord(character) for character in "0123456789:-")


def text(value: bytes) -> str:
    if b"\0" not in value:
        raise ValueError("unterminated theme text field")
    result = value.split(b"\0", 1)[0].decode("utf-8")
    if any(ord(character) < 0x20 or ord(character) == 0x7f for character in result):
        raise ValueError("control character in theme text")
    return result


def verify_layout(data: bytes) -> None:
    if len(data) != LAYOUT_BYTES:
        raise ValueError("unsupported theme layout size")
    magic, version, size, pages, slots, flags, reserved = struct.unpack_from("<I6H", data)
    if (magic, version, size, pages, slots, reserved) != (0x3154594C, 1, LAYOUT_BYTES, 32, 10, 0) or flags & ~7:
        raise ValueError("unsupported theme layout ABI")
    if any(value > 0xffffff for value in struct.unpack_from("<66I", data, 16)):
        raise ValueError("invalid theme ink")
    metrics = struct.unpack_from("<32h", data, 280)
    bounds = ((40, 60), (30, 60), (24, 72), (0, 24), (1, 48), (1, 48), (0, 80), (32, 180),
              (0, 16), (0, 48), (12, 28), (12, 28), (12, 28), (12, 28), (12, 28), (-8, 16),
              (0, 2), (0, 2), (0, 1000), (0, 1000), (0, 80), (0, 48), (0, 2), (0, 16),
              (0, 16), (0, 8), (60, 120), (40, 120), (24, 60), (0, 8), (0, 0), (0, 0))
    if any(not low <= metrics[key] <= high for key, (low, high) in enumerate(bounds)):
        raise ValueError("theme layout metric outside supported bounds")
    if 2 * metrics[29] >= metrics[0]:
        raise ValueError("theme focus padding consumes its row")
    if any(metrics[key] not in (12, 16, 18, 20, 28) for key in (10, 11, 12, 13, 14)):
        raise ValueError("unsupported theme font role")
    for offset in range(344, len(data), 8):
        x, y, width, height = struct.unpack_from("<4h", data, offset)
        if not (-240 <= x <= 240 and -240 <= y <= 240 and 0 <= width <= 240 and 0 <= height <= 240):
            raise ValueError("invalid theme rectangle")
    elements = [struct.unpack_from("<4h", data, 344 + i * 8) for i in range(8)]
    for i, (x, y, width, height) in enumerate(elements):
        if i == 5 and (width == 0) != (height == 0):
            raise ValueError("inconsistent optional speaker rectangle")
        if i != 5 and (not width or not height):
            raise ValueError("required theme element has zero area")
        if i in (0, 1) and (x < 0 or y < 0 or x + width > 240 or y + height > 240):
            raise ValueError("theme status element is off-screen")
    x, y, width, height = elements[3]
    if x < 0 or y < 0 or x + width > elements[1][2] or y + height > elements[1][3]:
        raise ValueError("theme battery fill exceeds its frame")
    for page in (1, 26):
        for slot in (0, 7, 9) + ((8,) if flags & 1 else ()):
            _, _, width, height = struct.unpack_from("<4h", data, 408 + (page * 10 + slot) * 8)
            if not width or not height:
                raise ValueError("required theme clock/date rectangle has zero area")


def verify_theme_bytes(package: bytes) -> dict:
    if not HEADER.size <= len(package) <= MAX_THEME_PACKAGE:
        raise ValueError("theme package length outside supported bounds")
    (magic, version, header_size, total, abi, entry_size, appearances, width, height,
     index, count, layout_offset, layout_size, theme_id, name, release, digest,
     reserved, crc) = HEADER.unpack_from(package)
    if (magic, version, header_size, total, abi, entry_size, width, height, index) != (
            b"XTHM", 1, 256, len(package), abi, 32, 240, 240, 256) or abi not in (1, 2, 3):
        raise ValueError("unsupported theme header/engine ABI")
    if not 0 < appearances <= 3 or not 0 < count <= MAX_RESOURCES or any(reserved):
        raise ValueError("invalid theme appearance/count/reserved fields")
    identity, display, release_text = text(theme_id), text(name), text(release)
    if not identity or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in identity):
        raise ValueError("unsafe theme identity")
    if not display or not release_text:
        raise ValueError("missing theme name/version")
    if zlib.crc32(package[:252]) & 0xffffffff != crc:
        raise ValueError("theme header CRC mismatch")
    if hashlib.sha256(package[256:]).digest() != digest:
        raise ValueError("theme payload SHA-256 mismatch")
    if layout_offset != index + count * ENTRY.size or layout_offset + layout_size > total:
        raise ValueError("invalid theme layout/index extents")
    verify_layout(package[layout_offset:layout_offset + layout_size])
    next_offset = layout_offset
    records = []
    styles = None
    for i in range(count):
        record = ENTRY.unpack_from(package, index + i * ENTRY.size)
        key, kind, flags, w, h, offset, size, resource_crc, r0, r1 = record
        if (not 0 < key <= 0xffff or key == 0x200 or flags & ~appearances or flags > 3 or
                r0 or r1 or offset != next_offset or not size or offset + size > total or w > 240 or h > 240):
            raise ValueError("invalid theme resource/brand slot/extent")
        if (i == 0 and (key, kind, flags, offset, size) != (1, 4, 0, layout_offset, layout_size)) or (i and key == 1):
            raise ValueError("theme layout must be first indexed resource")
        pixels = w * h
        if abi==3 and (count!=2 or (i==1 and (key,kind,flags,w,h)!=(3,7,0,0,0))):
            raise ValueError('ABI3 requires exactly LYT1 and NSC1')
        if kind in (1, 2, 3):
            if not pixels or size != pixels * {1: 1, 2: 3, 3: 2}[kind]:
                raise ValueError("invalid theme bitmap dimensions")
        elif kind == 4:
            if key != 1 or w or h or size != LAYOUT_BYTES:
                raise ValueError('invalid theme layout resource')
        elif kind == 5 and abi == 2:
            if flags or w or h or not 0x900 <= key < 0x908:
                raise ValueError('invalid theme font slot')
            verify_font(package[offset:offset + size])
        elif kind == 6 and abi == 2:
            if key != 2 or flags or w or h:
                raise ValueError('invalid theme presentation slot')
            styles = verify_presentation(package[offset:offset + size])
        elif kind==7 and abi==3:
            verify_native_scene(package[offset:offset+size])
        else:
            raise ValueError('unsupported theme resource format')
        if abi == 2 and ((key == 2 and kind != 6) or (0x900 <= key < 0x908 and kind != 5)):
            raise ValueError('reserved theme extension slot')
        for previous in records:
            if previous[0] == key and (not previous[2] or not flags or previous[2] & flags):
                raise ValueError("duplicate theme resource appearance")
        if zlib.crc32(package[offset:offset + size]) & 0xffffffff != resource_crc:
            raise ValueError("theme resource CRC mismatch")
        records.append(record)
        next_offset += size
    if next_offset != total:
        raise ValueError("theme package contains unindexed/trailing bytes")
    if abi == 2 and styles is None:
        raise ValueError('ABI2 requires STY2 presentation')
    for style in styles or []:
        fields, image, font = style[3], style[11], style[12]
        for appearance in (1, 2):
            if not appearances & appearance:
                continue
            for bit, resource, formats in ((16, image, (1, 2, 3)), (32, font, (5,))):
                if fields & bit and not any(r[0] == resource and r[1] in formats and
                        (not r[2] or r[2] & appearance) for r in records):
                    raise ValueError('missing STY2 image/font reference')
    for appearance in (1, 2):
        if abi==3:break
        if not appearances & appearance:
            continue
        required = REQUIRED_IMAGES + ((0x505,) if appearance == 2 else ())
        if any(0x800 <= record[0] < 0x880 for record in records):
            required += HOME_CLOCK_IMAGES
        for key in required:
            if not any(record[0] == key and record[1] in (1, 2, 3) and
                       (not record[2] or record[2] & appearance) for record in records):
                raise ValueError(f"theme required image missing: {key:#x}, appearance {appearance}")
    return dict(kind="theme", theme_id=identity, name=display, version=release_text,
                size=total, supported_appearances=appearances, header_crc32=crc,
                sha256=digest.hex(), resources=count, engine_abi=abi)


def verify_theme(path: pathlib.Path) -> dict:
    with path.open("rb") as file:
        package = file.read(MAX_THEME_PACKAGE + 1)
    return verify_theme_bytes(package)


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=pathlib.Path)
    print(json.dumps(verify_theme(parser.parse_args().package), ensure_ascii=False, indent=2))
