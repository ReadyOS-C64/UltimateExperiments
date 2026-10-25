"""Isolated actual C8/C11 width discovery on immutable f0a8 resident.

No shared editor build or VICE. Rebinds two NEW fields into the frozen frame's
free suffixes; current production UI/R1 remains40 columns. Independent source
row and navigation oracles never consume the product's row map or index.
"""
from pathlib import Path
from datetime import datetime, timezone
from bisect import bisect_right
import argparse, ctypes as C, hashlib, json, re, shutil, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor, editor_fixture
from peddle import Machine,VENDOR
from overlays import wrap,HEADER
BASE=ROOT/'build/style-editor/20261024T222858738847Z/fixture'
SHA='f0a803b7d0a8b7b254dc381ed548210240cd04b64080a5126399e7f4053610e0'
OWN=['src/overlays/navigation.s','src/overlays/layout.s','src/layout/state.s','src/layout/api.inc']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def symbols(kind,obj):
    return set(re.findall(r'Name:\s*"([^"\n]+)"',subprocess.run(['od65','--dump-'+kind,str(obj)],check=True,capture_output=True,text=True).stdout))
def build(out):
    fixture=out/'fixture';shutil.copytree(BASE,fixture)
    identity=json.loads((fixture/'freeze.json').read_text());assert identity['prg_sha256']==SHA==digest(fixture/'build/editor.prg')
    for name,h in identity['assets'].items():assert digest(fixture/f'build/overlays/{name}.seo')==h
    report=json.loads((fixture/'build/editor-report.json').read_text());s=dict(report['symbols']);s.update(se_v_columns=0x8CEE,se_n_view_columns=0x91FB)
    source=out/'source';shutil.copytree(ROOT/'src',source/'src');shutil.copy2(ROOT/'cfg/overlay-c.cfg',source/'overlay-c.cfg')
    # Only global resident symbols, not local branch labels from the link map.
    keys={n for n in s if n.startswith('se_') or n in ['text_ptr','screen_ptr'] or n.startswith('tui_')}
    lines=[f'{n} = ${s[n]:04X}' for n in sorted(keys)]
    lines+=['.macro OVL_BINDING',' .byte '+','.join('$'+report['resident_binding']['digest'][i:i+2] for i in range(0,32,2)),'.endmacro']
    (out/'editor-api.inc').write_text('\n'.join(lines)+'\n')
    for name,src in [('navigate','overlays/navigation'),('layout','overlays/layout'),('snapshot','diagnostics/snapshot'),('context','diagnostics/context'),('scan','diagnostics/scan'),('state','layout/state')]:
        command('ca65','-g','-I',out,'-I',source/'src','-o',out/f'{name}.o',source/f'src/{src}.s')
    objects=[out/f'{n}.o' for n in ['layout','snapshot','context','scan']]
    imports=set().union(*(symbols('imports',o) for o in objects));exports=set().union(*(symbols('exports',o) for o in objects))
    (out/'bindings.s').write_text('\n'.join(('.exportzp ' if s[n]<256 else '.export ')+n+'\n'+f'{n} = ${s[n]:04X}' for n in sorted(imports-exports))+'\n')
    command('ca65','-o',out/'bindings.o',out/'bindings.s')
    command('ld65','-C',source/'overlay-c.cfg','-o',out/'navigate.bin','-m',out/'navigate.map','-Ln',out/'navigate.lbl',out/'navigate.o')
    command('ld65','-C',source/'overlay-c.cfg','-o',out/'layout.bin','-m',out/'layout.map','-Ln',out/'layout.lbl',*objects,out/'bindings.o')
    # Separate state link proves declared widths fit their actual private slots.
    (out/'state.cfg').write_text('MEMORY { B:file="",start=$C000,size=$600; V:file="",start=$8CEE,size=$12; N:file="",start=$91FB,size=$5; } SEGMENTS { BSS:load=B,type=bss; VIEWSTATE:load=V,type=bss; NAVSTATE:load=N,type=bss; }')
    command('ld65','-C',out/'state.cfg','-o',out/'state.bin','-Ln',out/'state.lbl',out/'state.o')
    sizes={}
    for name,identity_ in [('navigate',8),('layout',11)]:
        payload=(out/f'{name}.bin').read_bytes();old=(fixture/f'build/overlays/{name}.seo').read_bytes()
        image=wrap(payload,1,identity_,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
        (fixture/f'build/overlays/{name}.seo').write_bytes(image)
        sizes[name]=dict(bytes=len(payload),baseline_bytes=len(old)-HEADER,delta=len(payload)-(len(old)-HEADER),sha256=hashlib.sha256(image).hexdigest())
    report['symbols']=s;(fixture/'build/editor-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'capsule.json').write_text(json.dumps(dict(resident_sha256=SHA,new_aliases={n:s[n] for n in ['se_v_columns','se_n_view_columns']},overlay_sizes=sizes,baseline=str(BASE),binding=report['resident_binding'],note='Resident PRG unchanged; report adds only two overlay-only frame aliases. New overlays assembled against exact old resident ABI digest. Production source snapshot is overlay derivation, not exact baseline resident source.'),indent=2)+'\n')
    return fixture,identity['names'],sizes

def fast_machine(out):
    cpp=out/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t lc_run(ZeroPagePeddle*m,uint64_t limit){auto b=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-b;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void lc_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void lc_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
    ext='.dylib' if sys.platform=='darwin' else '.so';lib=out/('runner'+ext)
    command('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',lib)
    runner=C.CDLL(str(lib));runner.lc_run.argtypes=[C.c_void_p,C.c_uint64];runner.lc_run.restype=C.c_uint64
    runner.lc_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];runner.lc_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
    class Fast(Machine):
        def call(self,address,a=0,x=0,y=0,limit=2_000_000):
            for n,v in [('a',a),('x',x),('y',y),('p',0x24),('sp',0xFD),('pc',address)]:getattr(self.lib,'zeropage_peddle_set_'+n)(self.handle,v)
            self.write(0x1FE,0xFE);self.write(0x1FF,2);n=runner.lc_run(self.handle,limit);assert n,('CPU did not return',hex(address),hex(self.regs().pc));return self.regs(),n
        def read_bytes(self,a,n):
            b=C.create_string_buffer(n);runner.lc_read(self.handle,a,n,b);return b.raw
        def reu(self):
            b=C.create_string_buffer(16*65536);runner.lc_reu(self.handle,len(b),b);return b.raw
    return Fast

def starts(source,width,nowrap=False):
    result=[0];p=0;column=0
    for byte in source:
        p+=1;column+=1
        if byte==13 or not nowrap and column==width:result.append(p);column=0
    return result

def next_row(source,p,width,nowrap=False):
    if nowrap:
        cr=source.find(b'\r',p);return len(source) if cr<0 else cr+1
    for _ in range(width):
        if p==len(source):break
        byte=source[p];p+=1
        if byte==13:break
    return p

def expected_map(source,top,caret,width,nowrap=False):
    # Walk canonical/merged bytes rather than consulting source checkpoints.
    row=[top]
    while True:
        bottom=next_row(source,row[-1],width,nowrap)
        seen=any(start<=caret<next_row(source,start,width,nowrap) or caret==len(source) and (start==caret or source.find(b'\r',start)<0 and (nowrap or len(source)-start<width)) for start in row)
        if len(row)==22 and seen:return tuple(row+[bottom])
        if len(row)==22:row=row[1:]
        row.append(bottom)
        assert len(row)<=22

def target(source,caret,width,command,preferred=None,nowrap=False):
    rows=starts(source,width,nowrap);index=bisect_right(rows,caret)-1;start=rows[index]
    logical=source.rfind(b'\r',0,caret)+1;end=source.find(b'\r',caret);end=len(source) if end<0 else end
    if command==40:return max(logical,caret-40),preferred
    if command==41:return min(end,caret+40),preferred
    if command==32:return logical,preferred
    if command==33:return end,preferred
    if command==34:return 0,preferred
    if command==35:return len(source),preferred
    if preferred is None:preferred=caret-start
    delta={36:-1,37:1,38:-21,39:21}[command];new=index+delta
    if new<0:return 0,preferred
    if new>=len(rows):return len(source),preferred
    begin=rows[new];end=source.find(b'\r',begin);end=len(source) if end<0 else end
    if not nowrap:end=min(end,begin+width)
    return min(begin+preferred,end),preferred

class Gate(editor_fixture.EditorFixture):
    def read(self,a,n):return self.m.read_bytes(a,n)
    def checkpoint(self):
        fields={'se_doc_original':5,'se_doc_append':5,'se_doc_epoch':2,'se_doc_generation':2,'se_doc_length':3,'se_doc_roots':256,'se_hot_ready':1,'se_hot_pending':1,'se_hot_original':5,'se_hot_append':5,'se_hot_generation':2,'se_hot_base':3,'se_hot_caret':3,'se_hot_old_length':2,'se_hot_length':2,'se_hot_left':2,'se_hot_right':2,'se_h_current':4,'se_h_saved':4,'se_h_counter':4,'se_h_end':2,'se_h_cursor':2,'se_sel_mark':1,'se_sel_anchor':3,'se_clip_token':5,'se_clip_length':3,'se_clip_active':1,'se_clip_busy':1,'se_clip_generation':2,'se_clip_epoch':2}
        return {n:self.read(self.s[n],w) for n,w in fields.items()}|{'gap':self.read(0x9200,2048),'screen':self.read(0x4000,1000),'color':self.read(0xD800,1000),'reu':self.m.reu()}
    def unchanged(self,before):
        now=self.checkpoint()
        for n,b in before.items():assert now[n]==b,('source/history/clipboard/view protection',n)
        assert self.read(0xC600,1024)==self.shim
    def raw(self,identity,op):
        self.put('se_overlay_frame',op,1);r,n=self.m.call(self.s['se_overlay_call'],a=identity,x=1);self.total_instructions+=n;return r
    def drain(self,op,limit=10000):
        calls=0
        while True:
            r=self.call('se_navigation_call',op);calls+=1
            assert not r.p&1,('continuation',op,hex(r.a),calls)
            if r.a==0:break
            assert r.a==1 and calls<limit,('budget',op,calls)
        return calls
    def layout(self,data,width,caret,mode=0,top=0,foreign=0):
        self.put('se_v_columns',width,1);self.put('se_l_mode',mode,1);self.put('se_v_top',top)
        if self.get('se_hot_caret')!=caret:self.position(caret)
        self.put('se_doc_read_locks',foreign,1)
        before=self.checkpoint();r=self.call('se_navigation_call',4);assert not r.p&1 and r.a==1
        assert self.get('se_doc_read_locks',1)==foreign+1
        calls=self.drain(5);self.unchanged(before);assert self.get('se_doc_read_locks',1)==foreign
        actual=tuple(int.from_bytes(self.read(self.s['se_v_rows']+3*i,3),'little') for i in range(22))+(self.get('se_v_bottom'),)
        expected=expected_map(data,min(top,caret),caret,width or 40,bool(mode))
        assert actual==expected,('map',width,caret,mode,top,actual,expected)
        assert self.get('se_n_view_columns',1)==(width or 40)
        return dict(width=width,caret=caret,mode=mode,top=actual[0],steps=calls,anchors=list(actual))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=args.out or ROOT/'build/layout-columns'/stamp;out.mkdir(parents=True)
    fixture,names,sizes=build(out)
    cpu_editor.ROOT=editor_fixture.ROOT=fixture;cpu_editor.NAMES=editor_fixture.NAMES=names;editor_fixture.Machine=fast_machine(out)
    f=Gate();cases=[];navigation=[];refusals=[];cancellations=[]
    try:
        data=b'\r'.join([b'A'*n for n in [0,1,39,40,41,59,60,61,79,80,81,127,128,129,257,511,1025]])+b'\r'
        f.source(data,banks=1,physical=8)
        for width in [0,40,60,80]:
            for caret in [0,1,40,60,80,127,128,129,799,880,1319,1759,len(data)-1,len(data)]:
                cases.append(f.layout(data,width,caret))
            for caret in [0,128,len(data)]:cases.append(f.layout(data,width,caret,mode=1))
            # The source-only ±40 command never follows display width.
            f.put('se_v_columns',width,1);f.put('se_l_mode',0,1)
            for caret in [2,180,900,len(data)]:
                for cmd in [32,33,36,37,38,39,40,41]:
                    f.position(caret);f.put('se_n_preferred_valid',0,1);f.put('se_r_valid',0,1);f.put('se_e_command',cmd,1)
                    before=f.checkpoint();r=f.call('se_navigation_call',1);assert not r.p&1
                    count=0 if not r.a else f.drain(2);f.unchanged(before)
                    wanted,pref=target(data,caret,width or 40,cmd)
                    assert f.get('se_e_target')==wanted,('navigation',width,caret,cmd,f.get('se_e_target'),wanted)
                    # Actual C8 reveal must produce a valid row anchor at the
                    # final target, rather than a numeric bound approximation.
                    top=f.get('se_v_top');rows=starts(data,width or 40)
                    assert top in rows and top<=wanted,('reveal top',width,cmd,top,wanted)
                    assert bisect_right(rows,wanted)-bisect_right(rows,top)<22,('reveal visibility',width,cmd,top,wanted)
                    navigation.append(dict(width=width,caret=caret,command=cmd,target=wanted,top=top,steps=count))
        # Pending gap with CR on both prefix/suffix sides; no flush/source write.
        f.source(data,banks=1,physical=8);f.position(128)
        for b in b'PENDING\rGAP':f.put('se_hot_byte',b,1);assert not f.call('se_hot_call',3).p&1
        base=f.get('se_hot_base');span=f.get('se_hot_length',2);left=f.get('se_hot_left',2);right=f.get('se_hot_right',2)
        gap=f.read(0x9200,left)+f.read(0x9200+right,2048-right);assert len(gap)==span
        merged=data[:base]+gap+data[base+f.get('se_hot_old_length',2):]
        for width in [40,60,80]:
            for caret in [f.get('se_hot_caret')]:cases.append(f.layout(merged,width,caret,foreign=1))
        assert f.get('se_hot_pending',1)==1
        # Invalid dimensions must leave all view/nav fields exactly as passed.
        f.source(data,banks=1,physical=8)
        for width in [1,39,41,59,61,79,81,128,255]:
            for identity,op in [(8,1),(11,4)]:
                f.put('se_v_columns',width,1);view=f.read(0x8C00,256);nav=f.read(0x9180,128);locks=f.get('se_doc_read_locks',1);before=f.checkpoint()
                r=f.raw(identity,op);assert r.p&1 and r.a==0x7B,('invalid width',width,identity,r.a)
                assert f.read(0x8C00,256)==view and f.read(0x9180,128)==nav
                assert f.get('se_doc_read_locks',1)==locks;f.unchanged(before);refusals.append(dict(width=width,identity=identity,error=r.a))
        for identity,begin,step in [(8,1,2),(11,4,5)]:
            for change in [60,80,1]:
                f.put('se_v_columns',40,1);f.put('se_e_command',35,1);f.put('se_v_top',0);f.put('se_doc_read_locks',1,1)
                before=f.checkpoint();r=f.raw(identity,begin);assert not r.p&1 and r.a==1
                f.put('se_v_columns',change,1);view=f.read(0x8C00,256);nav=f.read(0x9180,128)
                r=f.raw(identity,step);assert r.p&1 and r.a==(0x7B if change==1 else 0x74)
                assert f.read(0x8C00,256)==view and f.read(0x9180,128)==nav,('changed-width wrote continuation',identity)
                assert f.get('se_doc_read_locks',1)==2
                assert not f.call('se_navigation_call',3).p&1
                assert f.get('se_doc_read_locks',1)==1 and not f.get('se_n_owned',1);f.unchanged(before)
                cancellations.append(dict(identity=identity,width=change,retained_foreign_locks=1,error=r.a))
            # 0 and explicit40 are the same effective dimension.
            f.put('se_doc_read_locks',0,1);f.put('se_v_columns',0,1);f.put('se_e_command',35,1)
            r=f.raw(identity,begin);assert not r.p&1;f.put('se_v_columns',40,1);f.drain(step)
        # A foreign active owner cannot be overwritten, and exhausted lease
        # count cannot be decremented by admission-failure cleanup.
        f.put('se_v_columns',40,1)
        for identity,begin in [(8,1),(11,4)]:
            f.put('se_v_nav_busy',1,1);f.put('se_n_owned',1,1);f.put('se_doc_read_locks',2,1)
            view=f.read(0x8C00,256);nav=f.read(0x9180,128)
            r=f.raw(identity,begin);assert r.p&1 and r.a==0x7A
            assert f.read(0x8C00,256)==view and f.read(0x9180,128)==nav
            assert f.get('se_doc_read_locks',1)==2
            f.put('se_v_nav_busy',0,1);f.put('se_n_owned',0,1);f.put('se_l_active',0,1)
            f.put('se_doc_read_locks',255,1);f.put('se_e_command',35,1)
            before=f.checkpoint();r=f.call('se_navigation_call',begin)
            assert r.p&1 and r.a==0x41 and f.get('se_doc_read_locks',1)==255
            assert not f.get('se_n_owned',1) and not f.get('se_v_nav_busy',1);f.unchanged(before)
            cancellations.append(dict(identity=identity,retained_foreign_locks=255,error=r.a))
            f.put('se_doc_read_locks',0,1)
        # C11 must not overwrite the last navigation width: after a completed
        # intervening layout the next vertical command re-derives preference.
        data=b'A'*480+b'\r'+b'B'*480+b'\rEND'
        f.source(data,banks=1,physical=8)
        for oldwidth,width in [(40,60),(60,80),(80,40)]:
            f.put('se_n_columns',oldwidth,1);f.put('se_n_preferred',oldwidth-1,1);f.put('se_n_preferred_valid',1,1)
            cases.append(f.layout(data,width,159))
            f.put('se_e_command',37,1);f.put('se_r_valid',0,1)
            r=f.call('se_navigation_call',1);assert not r.p&1;f.drain(2)
            wanted,pref=target(data,159,width,37)
            assert f.get('se_e_target')==wanted and f.get('se_n_preferred',1)==pref
            navigation.append(dict(width=width,oldwidth=oldwidth,command=37,target=wanted,new_preferred=pref))
        # Many continuation packets and24-bit column/reveal arithmetic.
        data=b'Z'*66003+b'\rshort\r\r'+b'T'*70003+b'\rEND'
        f.source(data,banks=3,physical=12)
        for width in [40,60,80]:
            for caret in [65535,65536,66003,len(data)]:cases.append(f.layout(data,width,caret))
            cases.append(f.layout(data,width,66000,mode=1))
            f.put('se_v_columns',width,1);f.put('se_l_mode',1,1);f.position(66000);f.put('se_n_preferred_valid',0,1)
            wanted=66000
            for cmd in [37,37,37,36,36,36]:
                f.put('se_e_command',cmd,1);f.put('se_r_valid',0,1);r=f.call('se_navigation_call',1);assert not r.p&1;f.drain(2)
                wanted,_=target(data,wanted,width,cmd,66000,nowrap=True)
                assert f.get('se_e_target')==wanted and f.get('se_l_preferred')==66000
                f.position(wanted);navigation.append(dict(width=width,command=cmd,target=wanted,preferred24=66000))
            # Manual pan remains a fixed20 source columns and keeps the caret.
            for cmd,want in [(75,20),(75,40),(74,20),(74,0)]:
                f.put('se_e_command',cmd,1);r=f.call('se_navigation_call',1);assert not r.p&1;f.drain(2)
                assert f.get('se_l_pan')==want and f.get('se_hot_caret')==wanted
        result=dict(status='passed',baseline_resident_sha256=SHA,overlay_sizes=sizes,view_field_address=0x8CEE,nav_field_address=0x91FB,new_view_bytes=1,new_nav_bytes=1,new_resident_BSS_bytes=0,row_map_cases=len(cases),anchors_checked=23*len(cases),navigation_cases=len(navigation),invalid_dimensions=len(refusals),changed_width_cancellations=6,foreign_lease_refusals=2,cases=cases,navigation=navigation,refusals=refusals,cancellations=cancellations,total_instructions=f.total_instructions,limits='Actual changed C8/C11 on frozen resident; R1 renderer, mode UI, automatic horizontal pan width and final full-build/native gate remain parent integration work. No VICE or cycle/frame performance claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['cases','navigation','refusals','cancellations']},indent=2))
    except BaseException as e:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(e),symbols=f.s),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.m.reu());raise
    finally:f.close()
    evidence=ROOT/'agentsworking/evidence/M6'/(stamp+'-layout-columns');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'capsule')
    shutil.copy2(Path(__file__),evidence/'test_layout_columns.py');print('EVIDENCE',evidence)

if __name__=='__main__':main()
