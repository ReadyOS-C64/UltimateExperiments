"""Actual59 native GEOS clipped caret; explicit caller-input/PC/SP setup seam.

No source, geometry packets, cache authority, parser outputs or fonts are seeded.
ROM File/Open supplies source; IRQ GOTO/END/LEFT commands supply caret. PAL warp public
render completes through real foreground/IRQ scheduling. Not physical-key timing.
Owned binary8300/text8400..8439 only; no hardware/shared builds.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,socket,subprocess,zipfile
import test_presentation_vice as presentation
import test_plain_geos as plain
from test_presentation_vice import timing,capacity,Captured,vice_plan,ROOT
from d81_image import D81Image


def free_ports():
    for port in (8300,*range(8400,8440)):
        with socket.socket()as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',port))


def document():
    return timing.native.live.grid.native_text('Alpha ordinary text.\r'+'.'*160+'A\rTail.')


class Plan(presentation.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=8300
        p['global_defaults']['monitor_port_span']=1
        return p
    def caller_inputs(self,ident,caret,pan,anchor):
        # Real commands perform navigation's required derived-cache revocation.
        # Repeated direct root reload is not a substitute for that caller path.
        self.typed(ident+'_wrap_reset','wrap on')
        self.typed(ident+'_goto','goto '+('1'if caret==0 else'2'))
        if caret:self.send(ident+'_end_left',b'\x05\x9d')
        self.memory(ident+'_real_caret','se_hot_caret',caret,3)
        # Only no-wrap/pan/top/selection caller inputs are new monitor values.
        # Existing derived-valid bits are invalidated, never manufactured.
        def put(name,value,width=1):
            return f'> {self.s[name]:04x} '+value.to_bytes(width,'little').hex(' ')
        commands=['delete',f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',
                  put('se_l_mode',1),put('se_l_manual',1),put('se_l_pan',pan,3),put('se_v_top',0,3),
                  put('se_sel_mark',int(anchor is not None)),put('se_sel_anchor',anchor or 0,3),
                  put('se_l_valid',0),put('se_l_need_wrap',1)]
        self.raw(ident+'_caller_inputs',commands)


def package(e):
    data=document();source=e/'clipped.seq';source.write_bytes(data)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(source),'clipped,s'],capture_output=True)
    (e/'package-clipped.log').write_bytes(p.stdout+p.stderr);assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(b'CLIPPED',kind=1).data==data
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')


def scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True
    assert len(json.loads((e/'freeze.json').read_text())['catalog'])==59
    data=document();start=data.index(13)+1;edge=start+160
    n.boot();n.open('open_clipped',b'CLIPPED');n.typed('initial_full','syntax full');n.typed('initial_geos','mode hires')
    n.snapshot('baseline',data,3)
    cases=[('full-left-partial',3,1,0,None),('full-left-hidden',3,7,0,None),
           ('plain-left-partial',0,1,0,None),('full-left-selected',3,1,0,3),
           ('full-right-partial',3,1,edge,None),('full-right-hidden',3,0,edge,None)]
    current=3
    for ident,caps,pan,caret,anchor in cases:
        if caps!=current:
            n.typed(ident+'_preset','syntax '+('full'if caps==3 else'plain'));current=caps
        n.caller_inputs(ident,caret,pan,anchor)
        n.measure(ident,data,3,full=True,category='partially-clipped-source-caret')
        n.measurements[-1].update(caps=caps,pan=pan,caret_input=caret,anchor_input=anchor)
        for name,value,width in [('se_hot_caret',caret,3),('se_l_pan',pan,3),('se_l_mode',1,1),('se_l_manual',1,1),('se_v_top',0,3)]:
            n.memory(ident+'_input_'+name,name,value,width)
    return n


def state(f):
    return f.read(f.s['se_doc_roots'],512)+b''.join(f.read(f.s[name],width)for name,width in (
        ('se_doc_meta',15),('se_doc_length',3),('se_doc_generation',2),('se_doc_epoch',2),
        ('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),
        ('se_clip_token',5),('se_clip_length',3),('se_f_current_name',16),('se_f_current_len',1),('se_f_device',1)))


def evaluate(n):
    original=timing.semantic.expected
    def expected(f,data,fonts):
        bits,attrs,rows=plain.expected(f,data,fonts,f.get('se_render_caps',1));return bits,attrs,rows,None
    timing.semantic.expected=expected
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original
    s=n.s;cap=n.out/'captures';images=timing.native.live.grid.reu_images(n.out/'run')
    before_ram=(cap/'baseline-ram.bin').read_bytes();before_colors=(cap/'baseline-colors.bin').read_bytes()
    before_f=Captured(s,before_ram,before_colors,n.e);baseline=images['baseline'];canonical=state(before_f)
    ticket=before_f.read(s['se_bc_ticket'],8)+before_f.read(s['se_bc_head'],3)+before_f.read(s['se_bc_ring'],96)
    records=[];fonts={name:(n.e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)}
    for item in result['measurements']:
        ident=item['id'];ram=(cap/(ident+'-ram.bin')).read_bytes();reu=images[ident]
        f=Captured(s,ram,(cap/(ident+'-colors.bin')).read_bytes(),n.e)
        assert state(f)==canonical,(ident,'source/history/clipboard/filename/device')
        assert f.read(s['se_bc_ticket'],8)+f.read(s['se_bc_head'],3)+f.read(s['se_bc_ring'],96)==ticket,(ident,'observer tickets/ring changed')
        assert f.get('se_render_caps',1)==item['caps'] and f.get('se_hot_caret')==item['caret_input']
        assert f.get('se_l_pan')==item['pan'] and f.get('se_l_mode',1)==f.get('se_l_manual',1)==1
        assert f.get('se_v_top')==0 and not f.get('se_hot_pending',1) and not f.get('se_h_dirty',1)
        assert f.get('se_sel_mark',1)==int(item['anchor_input']is not None)
        if item['anchor_input']is not None:assert f.get('se_sel_anchor')==item['anchor_input']
        # Exact whole16MiB comparison: only actual typed FE cache bank writes.
        derived={bank for raw in(before_ram,ram)for bank in range(256)if raw[s['se_reu_physical_owner']+bank]==0xfe}
        wanted=bytearray(baseline)
        for bank in derived:
            assert bank and ram[s['se_reu_physical_owner']+bank]in(0,0xfe)
            wanted[bank*65536:(bank+1)*65536]=reu[bank*65536:(bank+1)*65536]
        assert reu==wanted,(ident,'whole16MiB outside actual FE; typed53/source/foreign immutable')
        handle=f.get('se_gc_handle',1);bank=ram[s['se_reu_map']+handle]
        assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfe
        raw=reu[bank*65536:(bank+1)*65536];assert raw[0]==1 and raw[2:4]==bytes((0x47,3))
        _,_,rows=plain.expected(f,document(),fonts,item['caps']);assert raw[1]==len(rows)
        member=[]
        for i,row in enumerate(rows):
            rec=raw[0x200+i*0x800:0x220+i*0x800]
            assert tuple(int.from_bytes(rec[o:o+3],'little')for o in(0,3,6))==(row.start,row.end,row.next)
            assert (rec[14],rec[15])==(row.height,row.top)
            owns=row.start<=item['caret_input']<=row.end
            assert bool(rec[26])==owns,(ident,'logical row member',i,rec.hex())
            if owns:member.append((i,row,rec))
        assert len(member)==1
        i,row,rec=member[0];widths=fonts['bsw9-widths.bin']
        origin=sum(widths[plain.geos.native(v)]for v in document()[row.start:item['caret_input']])-item['pan']
        advance=widths[plain.geos.native(document()[item['caret_input']])]
        point_visible=0<=origin<320;cell_visible=origin<320 and origin+advance>0
        assert bool(rec[18])==point_visible and bool(raw[45])==point_visible,(ident,'boundary witness',origin,rec.hex(),raw[:64].hex())
        assert raw[41]==f.get('se_v_seen',1)==1 and raw[42]==f.get('se_v_caret_row',1)==i
        if item['pan']:assert ram[0xcf90]==0,'R27 nonzero-pan conservative miss remains'
        records.append(dict(id=ident,caps=item['caps'],caret=item['caret_input'],pan=item['pan'],anchor=item['anchor_input'],
                            origin=origin,advance=advance,point_visible=point_visible,cell_intersects=cell_visible,
                            logical_member=True,seen=f.get('se_v_seen',1),row=i,prefix_hex=rec.hex(),
                            cycles=item['emulated_cycles'],loads=item['counter_deltas']['se_overlay_loads'],
                            bitmap_sha256=hashlib.sha256(ram[0x6000:0x7f40]).hexdigest(),
                            attrs_sha256=hashlib.sha256(ram[0x4000:0x43e8]).hexdigest()))
    assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
    free_ports()
    summary=dict(status='PASS',identity=result['identity'],scope=__doc__,frames=records,native_pixels=result['native_pixels'],
                 whole16MiB='immutable outside actual typed FE-derived bank(s); typed53 arena included in immutable comparison',
                 visual_review='pending',ports_released=True)
    (n.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True);return summary


def execute(source=None,existing=None,verify=False):
    free_ports()
    if existing:e=existing.resolve()
    else:
        e=timing.freeze(source.resolve(),'pal');target=e.with_name(e.name.replace('display-timing-pal','geos-clipped-caret-native'));e.rename(target);e=target;package(e)
    if verify:return evaluate(presentation.scenario_loaded(e))
    n=scenario(e);p=n.plan();assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in('tests','tools'):
            for path in(ROOT/folder).glob('*.py'):z.write(path,path.relative_to(ROOT))
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('NATIVE_CLIPPED_CARET',e,len(n.measurements),'frames',flush=True)
    capacity.run_owned_plan(p,n.out,timeout=900);return evaluate(n)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--existing',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
    execute(a.source,a.existing,a.verify)
