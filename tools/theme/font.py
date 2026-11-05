"""Build an explicit licensed FNT2 subset; no downloads or device operations."""
from pathlib import Path
import argparse,hashlib,json,re
from theme_presentation import FONT_HEADER,GLYPH,verify_font

def font_subset(path: Path, size: int, characters: str, *, line_padding: int | None = None) -> bytes:
    from PIL import ImageFont
    if not 8 <= size <= 48:
        raise ValueError('font size must be 8..48 native pixels')
    font = ImageFont.truetype(str(path), size)
    ascent, descent = font.getmetrics()
    codes = sorted({ord(c) for c in characters if ord(c) >= 0x20 and ord(c) != 0x7f})
    if not 1 <= len(codes) <= 1024 or ascent + descent > 64:
        raise ValueError('font subset exceeds device bounds')
    records, bitmaps = [], bytearray()
    top_ink,bottom_ink=0,0
    bitmap_offset = FONT_HEADER.size + len(codes) * GLYPH.size
    for code in codes:
        char = chr(code)
        mask, (left, top) = font.getmask2(char, mode='L', anchor='ls')
        w, h = mask.size
        if w and h:
            top_ink=min(top_ink,top);bottom_ink=max(bottom_ink,top+h)
        if w > 64 or h > 64:
            raise ValueError('glyph exceeds 64x64')
        raw = bytes(mask)
        start = len(bitmaps)
        for pixel in range(0, len(raw), 2):
            high = (raw[pixel] * 15 + 127) // 255
            low = (raw[pixel + 1] * 15 + 127) // 255 if pixel + 1 < len(raw) else 0
            bitmaps.append((high << 4) | low)
        records.append(GLYPH.pack(code, bitmap_offset + start, round(font.getlength(char)),
            w, h, left, -(top + h)))
    if line_padding is not None:
        if not 0<=line_padding<=8:raise ValueError('invalid font line padding')
        # A small streamed subset need not reserve the source font's unused
        # global ascenders. Keep every included glyph and its true baseline.
        ascent=-top_ink+line_padding;descent=bottom_ink+line_padding
    result = FONT_HEADER.pack(0x32544e46, 1, FONT_HEADER.size, len(codes), ascent + descent,
        descent, 0, bitmap_offset, bitmap_offset + len(bitmaps)) + b''.join(records) + bitmaps
    verify_font(result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--font',type=Path,required=True);p.add_argument('--characters',type=Path,required=True)
    p.add_argument('--license',type=Path,required=True);p.add_argument('--size',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--indexed',action='store_true',help='FNT3 common-name bank for theme ABI4/5');a=p.parse_args()
    sources={a.font.resolve(),a.characters.resolve(),a.license.resolve()}
    if a.output.resolve() in sources or a.output.with_suffix('.font.json').resolve() in sources:
        raise ValueError('Output would overwrite font source, character list or license')
    from fontTools.ttLib import TTFont
    chars=a.characters.read_text(encoding='utf8')
    if not a.license.is_file() or not a.license.read_bytes().strip():raise ValueError('Font license file is required')
    with TTFont(a.font) as font:
        names=[v.toUnicode() for v in font['name'].names if v.nameID in (1,4,6,16)]
        for name in names+[a.font.name]:
            norm=re.sub('[^a-z0-9]','',name.lower())
            if 'notosanssc' in norm or 'notosanscjksc' in norm:raise ValueError('Noto Sans SC is excluded by the project font policy')
        cmap=font.getBestCmap() or {}
        missing=sorted({ord(c) for c in chars if ord(c)>=32 and ord(c)!=127 and ord(c) not in cmap})
        if missing:raise ValueError('Source font is missing requested glyphs: '+','.join('U+%04X'%v for v in missing[:20]))
    if a.indexed:
        from theme_indexed_font import extend_font
        chars=''.join(sorted({c for c in chars if ord(c)>=32 and ord(c)!=127}))
        seed=font_subset(a.font,a.size,chars[:1024])
        data=extend_font(seed,a.font,a.size,chars)
    else:data=font_subset(a.font,a.size,chars)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
    proof={'format':'FNT3' if a.indexed else 'FNT2','font_name':a.font.name,'font_sha256':hashlib.sha256(a.font.read_bytes()).hexdigest(),
           'characters_sha256':hashlib.sha256(a.characters.read_bytes()).hexdigest(),
           'license_name':a.license.name,'license_sha256':hashlib.sha256(a.license.read_bytes()).hexdigest(),
           'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'hardware_tested':False}
    a.output.with_suffix('.font.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(proof,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,ImportError) as error:raise SystemExit('Font build failed: '+str(error))
