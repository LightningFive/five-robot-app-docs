"""Strict NSC1 data-only validator shared by theme packaging and installation."""
from __future__ import annotations
import struct
from theme_presentation import verify_font
from theme_indexed_font import verify_indexed_font
HEADER=struct.Struct('<4sHH10I8H');ASSET=struct.Struct('<HHHH6I')
SCENE=struct.Struct('<HHIII');NODE=struct.Struct('<BBHhhhhIHHIII')

def verify_native_scene(data:bytes)->dict:
    if len(data)<64:raise ValueError('truncated NSC1')
    magic,version,head,total,assets,scenes,aa,sa,na,nodes,pa,flags,meta,*fonts=HEADER.unpack_from(data)
    if version not in (1,2,3) or (magic,head,total,aa,sa,na,pa)!=(b'NSC1',64,len(data),64,64+assets*32,64+assets*32+scenes*16,64+assets*32+scenes*16+nodes*32):raise ValueError('NSC1 header/extents')
    if not 0<assets<=(1536 if version>=2 else 512) or not (1 if version>=2 else 93)<=scenes<=(192 if version>=2 else 128) or nodes>32768 or flags!=1 or not 0<meta<=assets or pa>len(data):raise ValueError('NSC1 bounds')
    records=[];end=pa;font_codes={}
    if version>=3 and scenes<140:raise ValueError('NSC3 missing system recipes')
    for i in range(assets):
        kind,w,h,res,at,size,crc,*pad=ASSET.unpack_from(data,aa+i*32)
        if res or any(pad) or at!=end or size>len(data)-at:raise ValueError('NSC1 asset extent')
        blob=data[at:at+size];end+=size
        if kind==2:
            if w or h:raise ValueError('NSC1 font geometry')
            packed = version>=3 and blob[:4]==b'FNT3'
            (verify_indexed_font if packed else verify_font)(blob)
            for n in range(struct.unpack_from('<H',blob,8)[0]):
                _,_,_,gw,gh,_,_=struct.unpack_from('<IIHBBhh',blob,24+n*(20 if packed else 16))
                if (gw*gh+1)//2>512:raise ValueError('NSC1 glyph exceeds bounded cache')
            font_codes[i]={struct.unpack_from('<I',blob,24+n*(20 if packed else 16))[0] for n in range(struct.unpack_from('<H',blob,8)[0])}
        elif kind==4:
            if w or h or size<4:raise ValueError('NSC1 literal')
            zh,en=struct.unpack_from('<HH',blob)
            if max(zh,en)>=256 or size!=4+zh+en:raise ValueError('NSC1 literal extent')
            for text in (blob[4:4+zh],blob[4+zh:]):
                value=text.decode('utf-8')
                if any((ord(c)<32 and c!='\n') or ord(c)==127 for c in value):raise ValueError('NSC1 literal controls')
        elif kind==5:
            if w or h or size<48:raise ValueError('NSC1 metadata')
        elif kind in (1,3,6):
            if kind==6 and (version<3 or size<16 or blob[7]):raise ValueError('NSC3 alpha mask header')
            if not 0<w<=240 or not 0<h<=240:raise ValueError('NSC1 image geometry')
            if kind==1:
                if size!=w*h*4:raise ValueError('NSC1 RGBA extent')
            else:
                if size<8:raise ValueError('NSC1 RLE header')
                header=8 if kind==6 else 4;pixel_bytes=1 if kind==6 else 4
                tw,th=struct.unpack_from('<HH',blob);base=header+(th+1)*4
                if not 0<tw<=w or not 0<th<=h or base>size:raise ValueError('NSC1 tile')
                previous=0
                for y in range(th):
                    a,b=struct.unpack_from('<II',blob,header+y*4)
                    if a!=previous or b<a or b>size-base or b-a>976:raise ValueError('NSC1 RLE extent')
                    pos=base+a;stop=base+b;x=0
                    while pos<stop:
                        ctl=blob[pos];pos+=1;count=(ctl&127)+1
                        amount=(1 if ctl&128 else count)*pixel_bytes
                        if count>tw-x or amount>stop-pos:raise ValueError('NSC1 RLE run')
                        x+=count;pos+=amount
                    if x!=tw:raise ValueError('NSC1 RLE row')
                    previous=b
                if base+previous!=size:raise ValueError('NSC1 RLE trailing bytes')
        else:raise ValueError('NSC1 asset kind')
        records.append((kind,w,h,at,size))
    if end!=len(data) or any(i>=assets or records[i][0]!=2 for i in fonts):raise ValueError('NSC1 fonts/payload')
    if flags:
        kind,w,h,at,size=records[meta-1];m=struct.unpack_from('<4sHH8I4H',data,at)
        if kind!=5 or m[:2]!=(b'NMD1',1) or m[2]>1024 or size!=48+m[2]*12 or any(c>0xffffff for c in m[3:11]) or m[11]>1 or m[12]>80 or m[13]>24 or m[14]:raise ValueError('NSC1 metadata bounds')
        previous=-1;symbol_keys=set();inline_bars={}
        for i in range(m[2]):
            key,ink,asset,res=struct.unpack_from('<IIHH',data,at+48+i*12);order=(key<<32)|ink
            if key>0xffff or ink>0xffffff and ink!=0xffffffff or res or asset>=assets or records[asset][0] not in (1,3,6) or order<=previous:raise ValueError('NSC1 symbol')
            previous=order
            if ink==0xffffffff:
                symbol_keys.add(key)
                if key in (0x520,0x521):inline_bars[key]=records[asset]
        required=set(range(0x100,0x119))|set(range(0x306,0x30b))|{0x400,0x401,0x403,0x404}|{0x600+ord(c) for c in '0123456789:-'}
        if version>=3 and not required<=symbol_keys:raise ValueError('NSC3 missing live symbol')
    first=0;maximum=0
    for i in range(scenes):
        sid,bindings,begin,count,kind=SCENE.unpack_from(data,sa+i*16)
        if sid!=i+1 or kind or not 0<count<=128 or bindings>128 or begin!=first or count>nodes-begin:raise ValueError('NSC1 scene')
        first+=count;maximum=max(maximum,count);seen=set();live=set();inline_slots=set()
        for j in range(count):
            kind,align,asset,x,y,w,h,color,binding,bits,a,b,c=NODE.unpack_from(data,na+(begin+j)*32)
            if kind not in (1,2) or align>2 or asset>=assets or not -240<=x<=240 or not -240<=y<=240 or not 0<w<=240 or not 0<h<=240 or color>0xffffff or bits&~(15|256|512|1024) or a&255>2 or (a>>8)&255>(8 if kind==2 else 32) or b>=240:raise ValueError('NSC1 node bounds')
            r=records[asset]
            semantic=(a>>8)&255
            if version>=3 and (kind==2 and semantic==8 or kind==1 and semantic in (19,20)):
                slot=(kind,semantic,b)
                if sid!=63 or a&255 or b>=(8 if kind==2 else 4) or slot in inline_slots:raise ValueError('NSC3 inline install slot')
                inline_slots.add(slot)
                if kind==1:
                    bar=inline_bars.get(0x520+semantic-19)
                    if not bar or bar[1:3]!=(w,h):raise ValueError('NSC3 inline install bar')
            live.add((kind,(a>>8)&255,b))
            if kind==1:
                if r[0] not in (1,3,6) or (w,h)!=r[1:3]:raise ValueError('NSC1 image node')
                if a&255 and (c>=assets or records[c][0] not in (1,3,6) or records[c][1:3]!=(w,h)):raise ValueError('NSC1 alternate image')
            else:
                if r[0]!=2 or binding>=bindings or binding in seen or c>0xffffff:raise ValueError('NSC1 text node')
                seen.add(binding);literal=a>>16
                if literal and (literal>assets or records[literal-1][0]!=4):raise ValueError('NSC1 text literal')
                if version>=3 and literal:
                    lr=records[literal-1];raw=data[lr[3]:lr[3]+lr[4]]
                    zh,en=struct.unpack_from('<HH',raw)
                    for text in (raw[4:4+zh],raw[4+zh:]):
                        if set(map(ord,text.decode()))-{10}-font_codes[asset]:raise ValueError('NSC3 missing literal glyph')
        if inline_slots and len(inline_slots)!=16:raise ValueError('NSC3 incomplete inline install template')
        if len(seen)!=bindings:raise ValueError('NSC1 missing binding')
        if version>=3:
            required=set()
            if 4<=sid<=9 or 131<=sid<=140:
                required={(2,2,0),(2,7,0),(1,1,0),(1,14,0),(1,2,0),(1,3,0)}|{(1,4,k) for k in range(5)}
            if 12<=sid<=32 or 63<=sid<=66 or sid in (70,71,84,118,128,129) or 112<=sid<=114:
                required|={(kind,sem,row) for kind,sem in ((2,3),(1,11)) for row in range(4)}
            if 72<=sid<=83 or 89<=sid<=101 or sid==117:required|={(2,7,21),(2,7,22)}
            if sid==102:required.add((2,7,13))
            if sid==103 or 105<=sid<=108:required|={(2,7,k) for k in (10,11,12)}
            if sid==104:required|={(2,7,k) for k in (10,14)}
            if not required<=live:raise ValueError(f'NSC3 missing live binding in recipe {sid}')
    if first!=nodes:raise ValueError('NSC1 unindexed nodes')
    return dict(assets=assets,scenes=scenes,maximum_active_nodes=maximum)
