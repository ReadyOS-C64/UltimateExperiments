"""Actual native selected-hidden fold summary proof; owned7700/7800..7839 only.

No product build or physical matrix claim. Uses the existing coherent .NET
capture handshake and independent fold projection model over native RAM.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
import test_grid_editor_vice as grid
import test_fold_builder as builder
from test_folds import action_model,Fold
from test_fold_locator import target_model
from test_fold_projection import expected
ROOT=grid.ROOT
sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,vice_plan
from vice_config import PROJECT
from d81_image import D81Image
from png_pixels import read_png
EXPECTED_PRG=None

def freeze():
    assert EXPECTED_PRG is None or json.loads((ROOT/'build/editor-report.json').read_text())['sha256']==EXPECTED_PRG
    sourcezip=ROOT/'build/fold-native-product-sources.zip'
    with zipfile.ZipFile(sourcezip,'w',zipfile.ZIP_DEFLATED) as z:
        for folder in ['src','cfg']:
            for p in (ROOT/folder).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(ROOT))
        z.write(ROOT/'Makefile','Makefile')
    grid.NAMES=list(cpu_editor.NAMES);e=grid.freeze(ROOT/'build',sourcezip,wide_colors=True)
    target=ROOT/'agentsworking/evidence/M5'/(e.name.replace('-grid-editor-native','-fold-selection-native'));shutil.move(e,target);e=target
    shutil.copy2(__file__,e/'test_fold_selection_vice.py');grid.package(e);return e

class FoldPlan(grid.GridPlan):
    def memory(self,*args,**kwargs):
        super().memory(*args,**kwargs);self.steps[-1]['retry']['max_attempts']=20
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=7700;p['global_defaults']['monitor_port_span']=1;return p
    def fold_capture(self,ident,data,folds,caret):
        self.memory(ident+"_top","se_v_top",0,3)
        self.memory(ident+'_caret','se_hot_caret',caret,3)
        self.capture_grid(ident,data,caret=caret)
        self.cases[-1]['folds']=[f.bytes().hex() for f in folds]

def scenario(e,full=False):
    r=json.loads((e/'editor-report.json').read_text());n=FoldPlan(e,r);data=grid.fixture();tree,_,_,error=builder.oracle(data);assert not error
    anchor=227;caret=294;target=target_model(tree,anchor,0);assert tree[target].hidden==anchor and tree[target].end==caret
    n.boot();n.open('open_diverse',b'DIVERSE');n.typed('goto_inside_basic','goto 14');n.send('actual_mark_inside',bytes([0x89]));n.typed('collapse_selected','fold')
    folds,_=action_model(tree,0,target,anchor,1,anchor);n.typed('goto_after_hidden_basic','goto 18')
    def capture(ident,ui=0,marked=True):
        n.memory(ident+'_anchor','se_sel_anchor',anchor,3);n.memory(ident+'_caret','se_hot_caret',caret,3)
        n.memory(ident+'_mark','se_sel_mark',int(marked));n.memory(ident+'_top','se_v_top',0,3)
        n.capture_grid(ident,data,caret=caret,mark=marked,ui=ui)
        n.cases[-1].update(group='same-source-history',folds=[x.bytes().hex() for x in folds],anchor=anchor)
    for mode in [0,1,2]:
        if mode:n.mode_to(mode)
        capture('selected'+str([40,60,80][mode]))
    n.send('actual_help',bytes([0x8B]),ui=1);capture('help80',ui=1)
    n.send('actual_close_help',bytes([0x8B]));capture('restored80')
    # Mark-off changes selection state only. Its inactive anchor remains227.
    n.send('actual_unmark',bytes([0x89]));capture('unmarked80',marked=False)
    return n

def execute(e,full):
    n=scenario(e,full);p=n.plan();assert len({x['id'] for x in p['steps']})==len(p['steps']);(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');print('PREPARED',n.out,len(p['steps']),len(n.cases),'screens',flush=True)
    project=grid.synchronous_project(n.out);vice_plan.PROJECT=project
    done=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(done.stdout+done.stderr);assert done.returncode==0,done.stdout+done.stderr
    artifacts,manifest=vice_plan.run_plan(p,n.out);print('CAPTURED',n.out,flush=True)
    return n,artifacts,manifest

class Captured:
    def __init__(self,s,ram,colors,e):
        self.s=s;self.ram=ram;self.colors=colors
        leaf=(e/'grid80.seo').read_bytes()[36:]
        self.fonts={'native8.bin':leaf[0xC00:0x1000],
                    'narrow4.bin':leaf[0x800:0xC00],
                    'narrow5.bin':(e/'grid60.seo').read_bytes()[36+0x800:36+0xC00]}
    def read(self,at,n):
        return self.colors[at-0xD800:at-0xD800+n] if at>=0xD800 else self.ram[at:at+n]
    def get(self,name,w=3):return int.from_bytes(self.read(self.s[name],w),'little')

def decoded_fold(raw):
    val=lambda a,n:int.from_bytes(raw[a:a+n],'little')
    return Fold(val(0,3),val(3,3),val(6,3),parent=val(9,2),depth=raw[11],kind=raw[12],flags=raw[13],saved=val(14,3),lines=val(17,3),level=raw[20],motion=val(21,4))

def evaluate(e,partial=False):
    e=Path(e);out=e/'editing';r=json.loads((e/'editor-report.json').read_text());s=r['symbols'];cases=json.loads((out/'cases.json').read_text());images=grid.reu_images(out/'run');freeze=json.loads((e/'freeze.json').read_text());palette={};observed=[];stable=None;tail=None;foreign=None
    planned_cases=len(cases);groups={}
    if partial:cases=[c for c in cases if (out/'captures'/(c['id']+'-ram.bin')).exists()]
    cache_regions={}
    for case in cases:
        prior=(out/'captures'/(case['id']+'-ram.bin')).read_bytes();handle=prior[s['se_gc_handle']]
        if handle:
            physical=prior[s['se_reu_map']+handle];assert prior[s['se_reu_logical_owner']+handle]==prior[s['se_reu_physical_owner']+physical]==0xFE;cache_regions.setdefault(case['group'],set()).add(physical)
    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];assert len(ram)==0xD000 and len(colors)==1000 and len(reu)==16*1024*1024
        f=Captured(s,ram,colors,e);get=f.get;data=bytes.fromhex(c['source']);folds=[decoded_fold(bytes.fromhex(x)) for x in c['folds']]
        def obj(identity,offset,length):
            result=bytearray()
            while length:
                count=min(length,65536-(offset&65535));logical=ram[s['object_extents']+identity*16+(offset>>16)];physical=ram[s['se_reu_map']+logical];assert ram[s['se_reu_logical_owner']+logical]==ram[s['se_reu_physical_owner']+physical]
                result+=reu[physical*65536+(offset&65535):physical*65536+(offset&65535)+count];offset+=count;length-=count
            return bytes(result)
        actual=bytearray()
        for i in range(get('se_doc_root_count',1)):
            root=f.read(s['se_doc_roots']+i*8,8);leaf=obj(get('se_doc_meta',1),root[0]*1024,root[1]*16)
            for j in range(root[1]):
                piece=leaf[j*16:(j+1)*16];identity=piece[0];assert int.from_bytes(piece[1:3],'little')==ram[s['object_gen_lo']+identity]+256*ram[s['object_gen_hi']+identity]
                actual+=obj(identity,int.from_bytes(piece[3:6],'little'),int.from_bytes(piece[6:9],'little'))
        assert bytes(actual)==data and get('se_doc_length')==len(data) and not get('se_hot_pending',1),(ident,'source')
        assert get('se_sel_mark',1)==int(c['mark']) and get('se_sel_anchor')==c['anchor'] and get('se_e_ui',1)==c['ui']
        assert get('se_hot_caret')==c['caret'] and get('se_mode',1)==c['mode'] and get('se_v_columns',1)==[0,60,80][c['mode']]
        for name in ['se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_n_owned','se_f_owner','se_st_request','se_input_nmi_pending']:assert get(name,1)==0,(ident,name,get(name,1))
        assert get('se_st_valid',1)==1 and get('se_input_head',1)==get('se_input_tail',1) and ram[0xC6]==0
        assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
        assert get('se_h_dirty',1)==int(c['dirty']) and (get('se_h_current',4)!=get('se_h_saved',4))==bool(c['dirty'])
        current=c['current'].encode();assert get('se_f_current_len',1)==len(current) and f.read(s['se_f_current_name'],len(current))==current
        # Metadata intervals/flags/saved canonical caret come from the independent
        # action model. The absolute motion serial is runtime state; immediate
        # restored-caret input assertions separately prove its equality rule.
        count=get('se_ef_count',2);assert count==len(folds)
        token=f.read(s['se_ef_token'],5);identity=token[0];assert ram[s['object_owner']+identity]==0x46
        raw=obj(identity,0,count*32)
        for i,fold in enumerate(folds):
            a,b=raw[i*32:(i+1)*32],fold.bytes();assert a[:21]==b[:21] and a[25:]==b[25:],(ident,'fold metadata',i,a.hex(),b.hex())
        wanted,anchors,ends,bits,seen=expected(f,data,folds,get('se_v_top'))
        actualanchors=tuple(int.from_bytes(f.read(s['se_v_rows']+i*3,3),'little') for i in range(22))+(get('se_v_bottom'),)
        assert actualanchors==anchors,(ident,actualanchors,anchors,get('se_v_top'))
        if get('se_ef_valid',1):assert tuple(int.from_bytes(f.read(s['se_ef_paint_ends']+i*3,3),'little') for i in range(22))==ends
        assert get('se_ef_fold_rows')==sum(x<<i for i,x in enumerate(bits))
        if c['mode']:
            assert f.read(0x6000,8000)==wanted[0],(ident,'independentbitmap')
            assert f.read(0x4000,1000)==wanted[1],(ident,'independentattrs')
            bitmap,attrs=wanted
        else:
            assert f.read(0x4000,1000)==wanted[0] and bytes(v&15 for v in colors)==wanted[1],(ident,'independent40cells/colors')
            bitmap=bytearray(8000);attrs=bytearray(1000);font=f.fonts['native8.bin']
            for i,code in enumerate(wanted[0]):
                row,col=divmod(i,40);bitmap[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in font[(code&127)*8:(code&127)*8+8]);attrs[i]=wanted[1][i]<<4|6
        w,h,pixels=read_png(out/f'native-{ident}.png');assert(w,h)==(384,272);palette.setdefault(6,pixels[0]);assert palette[6]==pixels[0]
        for y in range(200):
            row,gy=divmod(y,8)
            for x in range(320):
                col,gx=divmod(x,8);a=attrs[row*40+col];color=a>>4 if bitmap[row*320+col*8+gy]&(128>>gx) else a&15;actual=pixels[(y+35)*w+x+32];assert actual==palette.setdefault(color,actual),(ident,'nativepixel',x,y,color)
        assert len(set(palette.values()))==len(palette)
        for i,name in enumerate(freeze['catalog']):
            handle=get('se_overlay_asset' if i<16 else 'se_overlay_asset_second',1);ph=ram[s['se_reu_map']+handle];payload=(e/(name+'.seo')).read_bytes()[36:];assert reu[ph*65536+(i%16)*4096:ph*65536+(i%16)*4096+len(payload)]==payload
        cat=f.read(0x7F40,192)
        if tail is None:tail=cat
        assert cat==tail
        invariant=b''.join(f.read(s[n],width) for n,width in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_roots',256),('se_doc_root_count',1),('se_h_token',5),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        stable,foreign=groups.get(c['group'],(None,None))
        if stable is None:stable=invariant
        assert invariant==stable,(ident,'canonical/history/clipboard')
        masked=bytearray(reu);logical=ram[s['object_extents']+identity*16];ph=ram[s['se_reu_map']+logical];masked[ph*65536:ph*65536+count*32]=bytes(count*32)
        # First40 capture may precede lazy cache allocation. Mask the same
        # validated eventualFE extent on both sides, requiring it free before
        # allocation; a foreign owned bank is never exempted.
        for ph in cache_regions.get(c['group'],set()):
            assert ram[s['se_reu_physical_owner']+ph] in (0,0xFE)
            masked[ph*65536:ph*65536+5280]=bytes(5280)
        digest=hashlib.sha256(masked).hexdigest()
        if foreign is None:foreign=digest
        assert digest==foreign,(ident,'unowned REU or owned tails changed')
        groups[c['group']]=(stable,foreign)
        observed.append(dict(id=ident,mode=c['mode'],caret=c['caret'],fold_flags=[x.flags for x in folds],top=anchors[0],fold_rows=sum(x<<i for i,x in enumerate(bits))))
    saved=any(x['current']=='FOLDOUT' for x in cases)
    if saved:
        before=D81Image((e/'initial-fixtures.d81').read_bytes());after=D81Image((e/'working.d81').read_bytes());assert after.read(b'FOLDOUT',kind=1).data==grid.fixture()+b'X'
        assert {x.name for x in after.entries()}=={x.name for x in before.entries()}|{b'FOLDOUT'}
        for entry in before.entries():
            a,b=before.read(entry.name),after.read(entry.name);assert a.entry.raw[2:]==b.entry.raw[2:] and a.sectors==b.sectors and a.data==b.data,(entry.name,'foreigndiskchanged')
    if not saved:assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-only D81 changed'
    result=dict(status='partial' if partial else 'passed',planned_cases=planned_cases,saved_caret_restoration_asserted=any(c['id']=='expanded40' for c in cases),prg_sha256=r['sha256'],disk_sha256=freeze['disk_sha256'],screenshots=len(cases),native_pixels=len(cases)*64000,canonical_source_bytes=422,all_hidden_selection_set_by_actual_F2_fold_GOTO=True,catalog_assets=len(freeze['catalog']),REU_bytes=16*1024*1024,shim_bytes=1024,catalog_tail_bytes=192,mode_group_REU_preserved=True,allowed_changes='Within each unchanged-source/history mode group only exact fold records and5280 FE cache bytes; render/rebuild writes are separately checked by the CPU DMA audit; this native gate does not claim cross-mutation foreign REU immutability',cases=observed,limits='Actual native IRQ-byte commands and VIC pixels; no physical keymatrix or timingclaim. Source/caret/history/clipboard/catalog/shim and foreignD81 checked. Whole REU compared within each same-source mode group; no cross-mutation foreign-REU claim. Absolute motionserial encoding not compared.')
    (out/('partial-result.json' if partial else 'result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--run',type=Path);p.add_argument('--full',action='store_true');p.add_argument('--verify',type=Path);p.add_argument('--verify-partial',type=Path);a=p.parse_args()
    if a.freeze:print('FOLD_FREEZE',freeze(),flush=True)
    if a.run:execute(a.run.resolve(),a.full)
    if a.verify:evaluate(a.verify.resolve())
    if a.verify_partial:evaluate(a.verify_partial.resolve(),partial=True)
if __name__=='__main__':main()
