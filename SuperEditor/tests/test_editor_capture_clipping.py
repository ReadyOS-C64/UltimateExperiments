"""Packaged current-editor capture refusals and partial GEOS caret cells.

No asset substitutions, parser/layout outputs or derived-capability seeds.
Odd-pixel pan and selection are explicit caller inputs. C22 calls retain the
released whole64KiB scratch and whole16MiB read-only checks.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import test_cache_observer as ob
import test_plain_geos as plain

ROOT=ob.ROOT


def run(out,base):
    out.mkdir(parents=True);g=ob.Gate(out/'gate',base);f=g.f
    fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)}
    refused=[];frames=[];guard_count=0;held=None
    real_call=f.call
    writable=[(0,0x200),(0x4000,0x43e8),(0x5000,0x7f40),
              (0x8000,0x9180),(0x9c00,0xc600),(0xca00,0xcc00),(0xdf00,0xdf10)]
    def observed(name,a=0):
        nonlocal held,guard_count
        active=name=='se_editor_service'and f.get('se_e_job',1)==11 and f.m.read(0x9135)==22
        if active:
            ram=f.read(0,65536)
            if held is None:held=g.reu()
        result=real_call(name,a)
        if active:
            after=f.read(0,65536);cursor=0
            for lo,hi in writable:
                assert after[cursor:lo]==ram[cursor:lo],('C22 undeclared RAM',hex(cursor),hex(lo))
                cursor=hi
            assert after[cursor:]==ram[cursor:]
            guard_count+=1
            if f.m.read(0x9135)!=22 or f.get('se_e_error',1):
                assert g.reu()==held,'C22 wrote REU';held=None
        return result
    f.call=observed
    try:
        for width in (60,80):
            for name in ('se_f_owner','se_doc_read_locks','se_st_request','se_e_draw_busy','se_e_redraw'):
                f.source(b'Plain source.\rTail.',physical=256)
                f.typed(ob.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);f.render()
                f.put(name,1,1);phase=f.read(0x8d00,512);reu=g.reu()
                pixels=f.read(0x6000,8000)+f.read(0x4000,1000)
                f.put('se_overlay_frame',0,1)
                r,steps=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
                assert r.a==2 and not r.p&1
                assert f.read(0x8d00,512)==phase and g.reu()==reu
                assert f.read(0x6000,8000)+f.read(0x4000,1000)==pixels
                f.put(name,0,1);refused.append(dict(width=width,field=name,instructions=steps))
        specs=[('partial','Alpha text.\rMiddle.\r',1,0,None),
               ('visible','Alpha text.\r',0,0,None),
               ('hidden','Alpha text.\r',6,0,None),
               ('selection','Alpha text.\r',1,0,3),
               ('selection-reverse','Alpha text.\r',1,3,0),
               ('empty-CR','\rAfter',1,0,None),('empty-EOF','',1,0,None),
               ('EOF-partial','A',7,1,None),('EOF-hidden','A',11,1,None),
               ('native-code',':::basic\rPRINT "A"\r:::\r',1,9,None),
               ('right-partial','.'*160+'A\r',1,160,None),
               ('large-hidden','Alpha text.\r',65537,0,None)]
        for caps in (0,3):
            for tag,text,pan,caret,anchor in specs:
                data=ob.geos.native_text(text);f.source(data)
                f.typed(ob.geos.native_text('syntax '+('plain'if caps==0 else'full')))
                f.command(99);f.position(caret);f.render()
                f.put('se_sel_mark',int(anchor is not None),1)
                if anchor is not None:f.put('se_sel_anchor',anchor)
                f.put('se_l_mode',1,1);f.put('se_l_manual',1,1);f.put('se_l_pan',pan)
                f.put('se_v_top',0);f.m.write(0xcf90,0);f.m.write(0xcfe8,0)
                f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
                for warm in (False,True):
                    canonical=f.canonical();queue=g.queue();before=g.reu();start=f.total_instructions
                    f.render();bits,attrs,rows=plain.expected(f,data,fonts,caps)
                    assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(caps,tag,warm)
                    assert f.canonical()==canonical and g.queue()==queue and f.merged()==data
                    assert f.read(0xc600,1024)==f.shim and held is None
                    if pan:assert f.m.read(0xcf90)==0,'nonzero pan must retain conservative R27 miss'
                    after=g.reu();_,bank=f.raw_cache();lo=bank*65536
                    # Full render can update only this actual checked FE bank;
                    # individual C22 calls above have the stricter read-only rule.
                    assert after[:lo]==before[:lo] and after[lo+65536:]==before[lo+65536:]
                    name=str(caps)+'-'+tag+('-warm'if warm else'')
                    ob.geos.png(bits,attrs,out/(name+'.png'))
                    frames.append(dict(id=name,instructions=f.total_instructions-start,
                        pixels_sha256=hashlib.sha256(bits+attrs).hexdigest()))
        result=dict(status='PASS',scope=__doc__,fixture=g.identity,refusals=refused,
                    frames=frames,C22_wholeRAM_calls=guard_count,C22_whole16MiB_readonly=True)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('CAPTURE_CLIPPING_PASS',len(refused),len(frames),guard_count,flush=True)
        return result
    finally:f.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/editor-capture-clipping'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print('RUN',out,flush=True);run(out,a.fixture.resolve())
