"""Actual root40/60/80 integration; independent pixel/tile/source oracles.

Preparation is the default. --run uses a frozen editor catalog fixture (18..capacity assets). The private
batch runner executes the existing Peddle CPU unchanged; its one explicit ROM
read seam supplies actual chargen bytes only for the8 LDAabs,X instructions in
se_display_init. Actual copier stores/VIC/port instructions are never replaced.
CPU proof does not model physical ROM banking, IRQ/VIC timing or readability.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from peddle import Machine,VENDOR,library
from redraw_model import Screen,source40,screen_code,native_text,verify_screen
from test_style_editor import semantic_plan

EXPECTED={'gridedit','grid80','grid60'}
ROM_SEAM='Only actual se_display_init LDAabs,X character-ROM read results A/NZ substituted; physical banking requires VICE.'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def freeze(out,previous):
    target=out/'fixture'
    if previous:
        shutil.copytree(previous,target)
    else:
        names=list(cpu_editor.NAMES);catalog=json.loads((ROOT/'build/editor-report.json').read_text())['symbols']['se_overlay_capacity'];assert 18<=len(names)<=catalog<=64 and len(set(names))==len(names) and EXPECTED<=set(names),names
        (target/'build/overlays').mkdir(parents=True)
        for n in ['editor.prg','editor.lbl','editor.map','editor-report.json','editor-bindings.json','disk-manifest.json','supereditor.d81']:
            shutil.copy2(ROOT/'build'/n,target/'build'/n)
        for n in names:shutil.copy2(ROOT/f'build/overlays/{n}.seo',target/f'build/overlays/{n}.seo')
        (target/'fonts').mkdir()
        for n in ['native8.bin','narrow4.bin','narrow5.bin','manifest.json']:
            shutil.copy2(ROOT/'assets/fonts/generated'/n,target/'fonts'/n)
        manifest=json.loads((target/'fonts/manifest.json').read_text())
        raw=Path(manifest['native_source']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==manifest['native_sha256']
        (target/'fonts/chargen.bin').write_bytes(raw)
        identity=dict(names=names,prg_sha256=sha(target/'build/editor.prg'),
            assets={n:sha(target/f'build/overlays/{n}.seo') for n in names},
            fonts={p.name:sha(p) for p in (target/'fonts').iterdir()})
        (target/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
    identity=json.loads((target/'freeze.json').read_text())
    catalog=json.loads((target/'build/editor-report.json').read_text())['symbols']['se_overlay_capacity']
    assert 18<=len(identity['names'])<=catalog<=64 and len(set(identity['names']))==len(identity['names']) and EXPECTED<=set(identity['names'])
    assert set(identity['assets'])==set(identity['names'])
    assert sha(target/'build/editor.prg')==identity['prg_sha256']
    for n,h in identity['assets'].items():assert sha(target/f'build/overlays/{n}.seo')==h
    for n,h in identity['fonts'].items():assert sha(target/'fonts'/n)==h
    return target,identity


def runner(out):
    library() #existing CPU runtime; never an editor/shared make
    cpp=out/'runner.cpp'
    cpp.write_text('''#include "zeropage_peddle.h"
#include <cstdint>
#include <cstring>
static uint8_t rom[2048];static uint16_t loads[8];static uint64_t count=0;
static uint16_t active=0,entries[4]={};static uint8_t indices[2]={};static uint64_t totals[4]={};
static int nesting=-1;static uint16_t stop=0;static uint8_t stack=0;
extern "C" void gm_profile(uint16_t a,uint8_t first,uint8_t second,uint16_t row,uint16_t cell,uint16_t row60,uint16_t cell60){active=a;indices[0]=first;indices[1]=second;entries[0]=row;entries[1]=cell;entries[2]=row60;entries[3]=cell60;for(auto &n:totals)n=0;nesting=-1;}
extern "C" uint64_t gm_metric(int n){return totals[n];}
extern "C" void gm_rom(const uint8_t*r,const uint16_t*p){memcpy(rom,r,2048);memcpy(loads,p,16);count=0;}
extern "C" uint64_t gm_rom_count(){return count;}
static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);int offset=-1;
 if(nesting<0 && active && (r.pc==entries[0] || r.pc==entries[1] || r.pc==entries[2] || r.pc==entries[3])){
  auto id=zeropage_peddle_read(m,active);int leaf=id==indices[0]?0:id==indices[1]?1:-1;
  if(leaf>=0 && (r.pc==entries[leaf*2] || r.pc==entries[leaf*2+1])){nesting=r.pc==entries[leaf*2]?0:1;totals[nesting*2]++;
   stack=r.sp;stop=uint16_t(zeropage_peddle_read(m,0x100+uint8_t(stack+1)) |
       (zeropage_peddle_read(m,0x100+uint8_t(stack+2))<<8))+1;}}
 if(nesting>=0)totals[nesting*2+1]++;
 for(int i=0;i<8;i++)if(r.pc==loads[i])offset=i*256+r.x;
 zeropage_peddle_step_instruction(m);
 if(nesting>=0){auto after=zeropage_peddle_regs(m);if(after.pc==stop && after.sp==uint8_t(stack+2))nesting=-1;}
 if(offset>=0){auto v=rom[offset];auto p=zeropage_peddle_regs(m).p;
  zeropage_peddle_set_a(m,v);zeropage_peddle_set_p(m,(p&0x7d)|(v?0:2)|(v&0x80));count++;}}
extern "C" uint64_t gm_run(ZeroPagePeddle*m,uint64_t max){auto before=zeropage_peddle_regs(m).instructions;
 for(uint64_t i=0;i<max;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-before;step(m);}return 0;}
extern "C" uint64_t gm_idle(ZeroPagePeddle*m,uint16_t pc,uint64_t max){auto before=zeropage_peddle_regs(m).instructions;
 for(uint64_t i=0;i<max;i++){step(m);if(zeropage_peddle_regs(m).pc==pc)return zeropage_peddle_regs(m).instructions-before;}return 0;}
extern "C" void gm_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void gm_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
    ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('runner'+ext)
    subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',
        '-I'+str(VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True)
    dll=C.CDLL(str(path));dll.gm_rom.argtypes=[C.c_void_p,C.c_void_p];dll.gm_rom_count.restype=C.c_uint64
    dll.gm_profile.argtypes=[C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.c_uint16,C.c_uint16]
    dll.gm_metric.argtypes=[C.c_int];dll.gm_metric.restype=C.c_uint64
    dll.gm_run.argtypes=[C.c_void_p,C.c_uint64];dll.gm_run.restype=C.c_uint64
    dll.gm_idle.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64];dll.gm_idle.restype=C.c_uint64
    dll.gm_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p]
    dll.gm_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
    return dll


def row_starts(data,top,width,nowrap):
    starts=[top]
    for _ in range(22):
        p=starts[-1]
        if nowrap:
            end=data.find(b'\r',p);p=len(data) if end<0 else end+1
        else:
            for _ in range(width):
                if p==len(data):break
                byte=data[p];p+=1
                if byte==13:break
        starts.append(p)
    return tuple(starts)


def narrow_row(chars,flags,width,font,roles=None,colored=False):
    """Every pixel independently placed, then tile color chosen by ink votes."""
    pitch=5 if width==60 else 4;origin=10 if width==60 else 0
    bitmap=bytearray(320);votes=[[0]*14 for _ in range(40)]
    palette=[1,3,7,10,14,1,1,7,13,5,15,7,3,1] if colored else [1,7,3,7,3,3,3,3,3,3,14,14,14,14]
    priorities=[0,6,7,8,0,0,0,5,3,4,1,5,2,0]
    for col,byte in enumerate(chars):
        code=screen_code(byte);inverse=bool(flags[col]&6);reverse=bool(flags[col]&1);role=roles[col] if roles else 0
        for y in range(8):
            for x in range(pitch):
                physical=origin+col*pitch+x;ink=bool(font[code*8+y]&(128>>x))^reverse
                votes[physical//8][role]+=ink
                if ink^inverse:bitmap[(physical//8)*8+y]|=128>>(physical%8)
    attrs=bytes((palette[max(range(14),key=lambda r:(v[r],priorities[r] if v[r] else 0,-r))]<<4)|6 for v in votes)
    return bytes(bitmap),attrs


def projected_plan(data,anchors,width,pan):
    """Project independently classified source spans to variable row widths.

    The established semantic oracle emits40 columns per supplied source row.
    Two independently offset projections cover60/80 without borrowing product
    row buffers, plan bytes, role lookup tables or parser state.
    """
    left=semantic_plan(data,anchors,True,pan,lexical=True)
    if width==40:return left
    right=semantic_plan(data,anchors,True,pan+40,lexical=True)
    return b''.join(left[r*40:r*40+40]+right[r*40:r*40+width-40] for r in range(22))


def semantic_role(style):
    return style&15


class Fixture(editor_fixture.EditorFixture):
    def __init__(self,out,frozen,dll,colored=False):
        self.colored=colored
        self.out=out;self.dll=dll;self.report=json.loads((frozen/'build/editor-report.json').read_text());self.s=self.report['symbols']
        self.m=Machine();self.m.call=self.fast_call;self.total_instructions=0;self.max_service=0;self.peak=0;self.idle_steps=0;self.hold_file_transport=False;self.reu_guards=0
        self.assets={n:(frozen/f'build/overlays/{n}.seo').read_bytes() for n in cpu_editor.NAMES}
        self.fonts={n:(frozen/'fonts'/n).read_bytes() for n in ['native8.bin','narrow4.bin','narrow5.bin','chargen.bin']}
        self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)
        cpu_editor.startup(self.m,self.s,self.assets);self.settle()
        # Identify only the8 real linked ROM-load instruction PCs, requiring
        # their real following STAabs,X copier destinations. No writer is mocked.
        base=self.s['se_display_init'];code=self.read(base,96);pcs=[]
        for page in range(8):
            pattern=bytes([0xBD,0,0xD8+page,0x9D,0,0x48+page]);offset=code.index(pattern);pcs.append(base+offset)
        rom=self.fonts['chargen.bin'][2048:4096]
        self.dll.gm_rom(C.create_string_buffer(rom),(C.c_uint16*8)(*pcs))
        leaf=self.assets['grid80'][36:]
        assert leaf[39]==0x4C and leaf[42]==0x4C
        sixty=self.assets['grid60'][36:];assert sixty[39]==0x4C and sixty[42]==0x4C
        self.dll.gm_profile(self.s['se_overlay_active'],list(self.assets).index('grid80')+1,list(self.assets).index('grid60')+1,int.from_bytes(leaf[40:42],'little'),int.from_bytes(leaf[43:45],'little'),int.from_bytes(sixty[40:42],'little'),int.from_bytes(sixty[43:45],'little'))
        # MOS6510's internal port is not the wrapper's backing RAM[0/1]. Seed
        # it with actual instructions and query it by actual LDA, never fake a
        # mode transition's port semantics through host memory writes.
        self.m.load(0x0F80,bytes([0xA9,0x2F,0x85,0,0xA9,0x36,0x85,1,0x60]))
        self.m.load(0x0FA0,bytes([0xA5,1,0x60]));self.fast_call(0x0F80)
        assert self.cpu_port()&7==6
        self.call('se_display_init')
        assert self.read(0x4800,2048)==rom and self.dll.gm_rom_count()==2048,(
            'ROM read fixture',self.dll.gm_rom_count(),
            [(i,a,b) for i,(a,b) in enumerate(zip(self.read(0x4800,2048),rom)) if a!=b][:12])

    def fast_call(self,address,a=0,x=0,y=0,limit=8_000_000):
        for n,v in [('pc',address),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',y)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
        self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2)
        count=self.dll.gm_run(self.m.handle,max(limit,8_000_000));assert count,('nonreturn',hex(address),hex(self.m.regs().pc))
        self.peak=max(getattr(self,'peak',0),count);return self.m.regs(),count

    def call(self,name,a=0):
        if name=='se_editor_service' and self.hold_file_transport:
            assert self.get('se_e_job',1)!=9,'isolated File paint probe must never execute/fake DOS'
        r,n=self.fast_call(self.s[name],a=a);self.total_instructions+=n
        if name=='se_editor_service':self.max_service=max(self.max_service,n)
        return r

    def read(self,a,n):
        b=C.create_string_buffer(n);self.dll.gm_read(self.m.handle,a,n,b);return b.raw

    def reu(self):
        b=C.create_string_buffer(2*1024*1024);self.dll.gm_reu(self.m.handle,len(b),b);return b.raw

    def reu_safe(self,before,tag):
        after=self.reu();self.reu_guards+=1
        if 'se_gc_handle' not in self.s:assert after==before,(tag,'wholeREU changed');return True
        handle=self.get('se_gc_handle',1)
        if handle:
            assert self.get('se_gc_epoch',2)==self.get('se_reu_epoch',2)
            assert self.m.read(self.s['se_reu_logical_owner']+handle)==0xFE
            physical=self.m.read(self.s['se_reu_map']+handle)
            assert physical and self.m.read(self.s['se_reu_physical_owner']+physical)==0xFE
            start=physical*65536;masked=bytearray(after)
            for lo,hi in ((0,22*240),(0x1500,0x1680)):
                masked[start+lo:start+hi]=before[start+lo:start+hi]
            assert bytes(masked)==before,(tag,'noncacheREU/FEbanktail changed')
        else:assert after==before,(tag,'REU changed withoutvalidFEcachetoken')
        return True

    def cpu_port(self):return self.fast_call(0x0FA0)[0].a

    def catalog(self):
        raw=self.read(self.s['se_overlay_ids'],6*self.s['se_overlay_capacity'])
        if 'se_overlay_managed_verification' in self.s:
            from overlay_catalog_policy import catalog_identity
            return catalog_identity(raw,self.s)
        return raw

    def source(self,data,banks=2,physical=32):
        self.logical=data;super().source(data,banks,physical);self.put('se_status',1,1)

    def merged(self):
        data=self.document()
        if not self.get('se_hot_ready',1):return data
        base=self.get('se_hot_base');gap=self.read(0x9200,self.get('se_hot_left',2))+self.read(0x9200+self.get('se_hot_right',2),2048-self.get('se_hot_right',2))
        return data[:base]+gap+data[base+self.get('se_hot_old_length',2):]

    def canonical(self):
        fields=[('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),
            ('se_hot_ready',1),('se_hot_pending',1),('se_hot_base',3),('se_hot_caret',3),
            ('se_hot_before',3),('se_hot_group',1),('se_hot_left',2),('se_hot_right',2),
            ('se_sel_mark',1),('se_sel_anchor',3),('se_h_current',4),('se_h_saved',4),
            ('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_h_group',1),
            ('se_h_open_group',1),('se_clip_token',5),('se_clip_length',3)]
        return self.read(self.s['se_doc_roots'],512)+b''.join(self.read(self.s[n],w) for n,w in fields)+self.read(0x9200,2048)

    def queued(self,key,mods=0):
        at=self.get('se_input_head',1);assert (at+1)&63!=self.get('se_input_tail',1)
        for n,v in [('se_input_chars',key),('se_input_mods',mods),('se_input_matrix',0x40)]:self.m.write(self.s[n]+at,v)
        self.put('se_input_head',(at+1)&63,1)

    def tick(self):
        for n,v in [('pc',self.s['se_idle']),('sp',0xFF),('p',0x24),('a',0),('x',0),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
        count=self.dll.gm_idle(self.m.handle,self.s['se_idle'],8_000_000);assert count,'idle nonreturn'
        self.total_instructions+=count;self.peak=max(self.peak,count)
        self.idle_steps+=1

    def debug(self):
        return {n:self.get(n,w) for n,w in [('se_e_job',1),('se_e_redraw',1),('se_f_owner',1),('se_st_request',1),('se_st_valid',1),('se_st_busy',1),('se_fs_owned',1),('se_doc_read_locks',1),('st_phase',1),('st_lex_phase',1)]}

    def begin_style(self):
        self.render()
        for _ in range(100):
            if self.get('se_f_owner',1)==2:
                assert self.get('se_st_busy',1) and self.get('se_fs_owned',1);return
            self.tick()
        raise AssertionError(('style did not acquire',self.debug()))

    def until_lexical(self,phase):
        for _ in range(100000):
            assert self.get('se_f_owner',1)==2 and self.get('se_st_busy',1),self.debug()
            if self.get('st_lex_phase',1)==phase:return
            self.tick()
        raise AssertionError(('missing lexical phase',phase,self.debug()))

    def finish_style(self,valid=True):
        for _ in range(100000):
            if not self.get('se_e_job',1) and not self.get('se_e_redraw',1) and self.get('se_f_owner',1)!=2 and self.get('se_st_request',1)!=1:
                assert bool(self.get('se_st_valid',1))==valid,self.debug();return
            self.tick()
        raise AssertionError(('style nonconvergence',self.debug()))

    def recolor(self):
        for _ in range(100000):
            if not self.get('se_e_job',1) and not self.get('se_e_redraw',1) and self.get('se_st_valid',1) and self.get('se_f_owner',1)==0:return
            self.tick()
        raise AssertionError('source40 style never completes')

    def mode(self,command,target,route='direct'):
        canonical,reu,catalog=self.canonical(),self.reu(),self.catalog();port=self.cpu_port()
        old=self.get('se_mode',1);copies=self.dll.gm_rom_count()
        if route=='direct':self.command(command)
        elif route=='typed':self.typed(native_text(f'mode {40 if target==0 else 60 if target==1 else 80}'))
        else:
            self.queued(0x8C,4 if route=='CTRL-F8' else 0);self.tick();self.settle()
        assert self.get('se_mode',1)==target,(command,route,self.get('se_mode',1))
        assert self.get('se_v_columns',1)==[0,60,80][target]
        assert not self.get('se_st_valid',1) and not self.get('se_st_request',1)
        assert self.cpu_port()==port
        if target==0 and old:
            # The logical mode command now leaves the old bitmap frame live.
            # The actual 40-column painter restores the character ROM image
            # immediately before its first text-screen write.
            assert self.m.read(0xD011)&0x20
            assert self.dll.gm_rom_count()==copies
        assert self.canonical()==canonical and self.reu()==reu and self.catalog()==catalog,(route,'mode mutated source/group/REU/catalog')

    def remove(self,identity,slot):
        at=next(i for i in range(self.s['se_overlay_capacity']) if self.m.read(self.s['se_overlay_ids']+i)==identity and self.m.read(self.s['image_slot']+i)&0x7F==slot)
        self.m.write(self.s['se_overlay_ids']+at,0);self.m.write(self.s['se_overlay_active']+slot,0);return at

    def close(self):
        self.rom_reads=self.dll.gm_rom_count()
        if sys.exc_info()[0] and not (self.out/'failed-state').exists():
            d=self.out/'failed-state';d.mkdir();(d/'c64.bin').write_bytes(self.read(0,65536));(d/'reu.bin').write_bytes(self.reu())
            (d/'source.bin').write_bytes(getattr(self,'logical',b''));(d/'symbols.json').write_text(json.dumps(self.s,indent=2)+'\n')
        self.m.close()


def logical_ui(f,data):
    base=source40(data,f.get('se_v_top'),f.get('se_hot_caret'),marked=bool(f.get('se_sel_mark',1)),anchor=f.get('se_sel_anchor'),pending=bool(f.get('se_hot_pending',1)),dirty=bool(f.get('se_h_dirty',1)),error=f.get('se_e_error',1),history_fault=bool(f.get('se_h_fault',1)),trimmed=bool(f.get('se_h_trimmed',2)))
    matrix,colors=bytearray(base.matrix),bytearray(base.colors);rect=None
    def text(value,row,col):
        raw=bytes(map(screen_code,native_text(value)));assert col+len(raw)<=40,(value,col)
        matrix[row*40+col:row*40+col+len(raw)]=raw
    def box(x,y,w,h,border_color=14,attached=False):
        nonlocal rect
        rect=(x,y,w,h)
        for row in range(h):
            for col in range(w):
                at=(y+row)*40+x+col;border=row in (0,h-1) or col in (0,w-1)
                glyph=32
                if row==0:
                    if col==0:glyph=(0x6B if attached and x==0 else 0x72 if attached else 0x70)
                    elif col==w-1:glyph=(0x73 if attached and x+w==40 else 0x72 if attached else 0x6E)
                    else:glyph=0x40
                elif row==h-1:glyph=0x6D if col==0 else 0x7D if col==w-1 else 0x40
                elif col in (0,w-1):glyph=0x5D
                matrix[at]=glyph;colors[at]=border_color if border else 1
    ui=f.get('se_e_ui',1)
    if ui==2:
        matrix[960:]=bytes([32])*40;text('Command:',24,0)
        raw=f.read(f.s['se_e_text'],f.get('se_e_text_length',1));matrix[968:968+len(raw)]=bytes(map(screen_code,raw));matrix[968+len(raw)]=0xA0
    elif ui==1 and f.get('se_e_menu',1)==1:
        box(0,1,21,5,7,True)
        for i,label in enumerate(['O Open...  CTRL-O','S Save     CTRL-S','A Save as...']):
            text(label,i+2,2)
            if i==f.get('se_e_item',1):
                for col in range(len(label)):at=(i+2)*40+2+col;matrix[at]^=128;colors[at]=7 if col==0 else 3
            else:colors[(i+2)*40+2]=3
    elif ui==1 and f.get('se_e_menu',1)==9:
        box(1,3,38,16)
        for row,label in [(4,'SuperEditor keys 1/3'),(6,'Type; RETURN/DEL/cursors'),(7,'F1 menu; F6 help; F7 command'),(8,'CBM-S settings; F8 modes'),(9,'F3/F5, CBM-UP/DOWN: pages'),(10,'CBM-LEFT/RIGHT: jump 40'),(11,'CBM-F toggle region'),(12,'CBM-D collapse; CBM-E expand'),(13,'F2 mark; CTRL-C/K copy; X/V cut/pst'),(14,'F4 wrap; HOME/CTRL-E line'),(17,'F6/STOP closes help')]:text(label,row,3)
    elif ui==3:
        box(1,4,38,19);text('Open a PETSCII document',5,3)
        colors[203:238]=bytes([7])*35;text('Device:',6,3);matrix[250]=48+f.get('se_f_device',1);text('Name:',7,3)
        name=f.read(f.s['se_f_name'],f.get('se_f_name_len',1));matrix[290:290+len(name)]=bytes(map(screen_code,name));matrix[290+len(name)]=0xA0;colors[290:291+len(name)]=bytes([3])*(len(name)+1)
        if f.get('se_f_ui_help',1):
            for row,label in [(10,'Type up to 16 PETSCII characters.'),(12,'RETURN accepts the name.'),(14,'F3 drive F5 page DEL erase'),(18,'S Save   D Discard   C Cancel'),(16,'STOP cancels; F6 help.')]:text(label,row,3)
        else:
            assert f.get('se_fd_list_count',1)==0 and not f.get('se_fd_confirm',1),'only pre-DOS empty filename modal is in this oracle'
            text('UP/DOWN choose; RETURN accepts',18,3);text('F3 drive 8/9  F5 page',19,3)
        status=' File dialog       F6 Help   STOP Back   '
        assert status[40:]==' ' #legacy painter's harmless screen-padding blank
        text(status[:40],24,0)
    elif ui not in (0,1,4):raise AssertionError(('unsupported popup',ui))
    if rect:assert tuple(f.get(n,1) for n in ['tui_box_x','tui_box_y','tui_box_w','tui_box_h'])==rect
    return matrix,colors,rect


def expected(f,data):
    width=[40,60,80][f.get('se_mode',1)];top=f.get('se_v_top');nowrap=f.get('se_l_mode',1);pan=f.get('se_l_pan') if nowrap else 0
    anchors=row_starts(data,top,width,nowrap);caret=f.get('se_hot_caret');mark=f.get('se_sel_mark',1);lo,hi=sorted((caret,f.get('se_sel_anchor'))) if mark else (0,0)
    logical,ui_colors,rect=logical_ui(f,data)
    if width==40:
        plan=semantic_plan(data,anchors,nowrap,pan,lexical=True) if f.get('se_st_valid',1) else bytes(880)
        seen=None
        for row,(start,stop) in enumerate(zip(anchors,anchors[1:])):
            end=stop-1 if stop>start and data[stop-1]==13 else stop
            for col in range(40):
                p=start+pan+col;glyph=32;ink=1
                if p<=end:
                    glyph=screen_code(data[p]) if p<end else 32
                    style=plan[row*40+col] if p<end else 0
                    glyph^=style&128;under=glyph;ink=[1,3,7,10,14,1,1,7,13,5,15,7,3,1][style&15]
                    if lo<=p<hi:glyph^=128;ink=3
                    if p==caret and seen is None:glyph=under^128;ink=7 if mark else 3;seen=(row,col)
                physical=row+2
                if rect:
                    x,y,w,h=rect
                    if y<=physical<y+h and x<=col<x+w:continue
                at=physical*40+col;logical[at]=glyph;ui_colors[at]=ink
        return (bytes(logical),bytes(ui_colors)),anchors,seen,rect
    font=f.fonts['narrow5.bin' if width==60 else 'narrow4.bin'];bits=bytearray(8000);attrs=bytearray([0x16])*1000;seen=None
    plan=projected_plan(data,anchors,width,pan) if f.colored and f.get('se_st_valid',1) else bytes(width*22)
    for row,(start,stop) in enumerate(zip(anchors,anchors[1:])):
        end=stop-1 if stop>start and data[stop-1]==13 else stop
        chars=[];flags=[];roles=[]
        for col in range(width):
            p=start+pan+col;chars.append(data[p] if p<end else 32);style=plan[row*width+col] if p<end else 0
            roles.append(semantic_role(style));flag=1 if style&128 else 0
            if p<=end:
                if lo<=p<hi:flag|=2
                if p==caret and seen is None:flag|=4;seen=(row,col)
            flags.append(flag)
        rowbits,rowattrs=narrow_row(chars,flags,width,font,roles,f.colored);bits[(row+2)*320:(row+3)*320]=rowbits;attrs[(row+2)*40:(row+3)*40]=rowattrs
    ui={(r,c) for r in [0,1,24] for c in range(40)}
    if rect:
        x,y,w,h=rect;ui.update((r,c) for r in range(y,y+h) for c in range(x,x+w))
    native=f.fonts['native8.bin']
    for row,col in ui:
        at=row*40+col;code=logical[at];glyph=native[(code&127)*8:(code&127)*8+8]
        bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in glyph);attrs[at]=((ui_colors[at]&15)<<4)|6
    return (bytes(bits),bytes(attrs)),anchors,seen,rect


def run(out,previous,colored=False):
    frozen,identity=freeze(out,previous);editor_fixture.ROOT=cpu_editor.ROOT=frozen;editor_fixture.NAMES=cpu_editor.NAMES=identity['names']
    paths=[Path(__file__),ROOT/'tools/peddle.py',ROOT/'tools/editor_fixture.py',
        ROOT/'tools/cpu_editor.py',ROOT/'tools/redraw_model.py',
        ROOT/'tools/supermark_model.py',ROOT/'tests/test_style_editor.py']
    source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT))
    dll=runner(out);frames=[];cases=[];instances=[];style_intervals=[]
    def fixture(data):
        f=Fixture(out,frozen,dll,colored);f.source(data)
        if not colored:f.typed(native_text('syntax plain'))
        instances.append(f);return f
    def check(f,data,tag,filemodal=False,published=False):
        f.logical=data;canonical,reu,catalog=f.canonical(),f.reu(),f.catalog()
        instructions=f.total_instructions;metrics=[dll.gm_metric(i) for i in range(4)]
        if filemodal:
            # Approved isolated lane: keep the real directory CE request held,
            # drain only actual NAV/job7 preparation, then publish the popup.
            # A completed paint may retain job9; never run or fake its provider.
            for _ in range(8):
                sequence=f.get('se_e_draw_sequence',2)
                assert not f.call('se_editor_render').p&1
                if f.get('se_e_job',1)==7:
                    for step in range(30000):
                        if f.get('se_e_job',1)!=7:break
                        f.call('se_editor_service')
                    else:raise AssertionError('File modal NAV preparation did not finish')
                    continue
                if f.get('se_e_draw_sequence',2)!=sequence:break
            else:raise AssertionError('File modal paint did not publish')
        elif not published:
            sequence=f.get('se_e_draw_sequence',2)
            f.render()
            if f.get('se_st_request',1)==1:
                assert f.colored and not f.get('se_st_valid',1)
                armed=f.get('se_e_draw_sequence',2)
                assert armed==sequence+(f.get('se_mode',1)==0)
                f.finish_style()
                assert f.get('se_e_draw_sequence',2)==armed+1
                # C33 legitimately allocated/populated its first FE cache while
                # completing the transaction. Verify the published frame from
                # this stable boundary without invoking render a second time.
                canonical,reu,catalog=f.canonical(),f.reu(),f.catalog()
        wanted,anchors,seen,rect=expected(f,data)
        if f.get('se_mode',1):
            assert f.read(0x6000,8000)==wanted[0],(tag,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(f.read(0x6000,8000),wanted[0])) if a!=b))
            assert f.read(0x4000,1000)==wanted[1],(tag,'attributes')
            if not f.colored:assert not f.get('se_st_valid',1) and not f.get('se_st_request',1)
            assert [f.m.read(a) for a in [0xD011,0xD016,0xD018]]==[0x3B,8,8]
        else:
            verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),Screen(*wanted,anchors,seen),tag=tag)
            assert [f.m.read(a) for a in [0xD011,0xD016,0xD018]]==[0x1B,8,2]
            display_rom=bytearray(f.fonts['chargen.bin'][2048:])
            display_rom[0x6d*8:0x6e*8]=f.fonts['native8.bin'][0x6d*8:0x6e*8]
            display_rom[0x7d*8:0x7e*8]=f.fonts['native8.bin'][0x7d*8:0x7e*8]
            assert f.read(0x4800,2048)==bytes(display_rom)
        actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
        assert actual==anchors,(tag,'23anchors',actual,anchors)
        assert f.get('se_v_seen',1)==int(seen is not None)
        if seen:assert (f.get('se_v_caret_row',1),f.get('se_v_caret_col',1))==seen
        assert f.merged()==data and f.canonical()==canonical and f.reu_safe(reu,tag) and f.catalog()==catalog,(tag,'render mutated canonical/REU/catalog')
        if f.colored and f.get('se_st_valid',1):
            width=[40,60,80][f.get('se_mode',1)];pan=f.get('se_l_pan') if f.get('se_l_mode',1) else 0
            plan=projected_plan(data,anchors,width,pan);raw=f.read(0x4400 if width==40 else 0x4800,width*22)
            # Cold C14 deliberately does not clear padding in the aliased font
            # window. C33 consumes only live source cells and forces padding to
            # role0; the independent final pixel/attribute oracle checks that.
            for row,(start,stop) in enumerate(zip(anchors,anchors[1:])):
                end=stop-1 if stop>start and data[stop-1]==13 else stop
                count=min(width,max(0,end-(start+pan)));at=row*width
                assert raw[at:at+count]==plan[at:at+count],(tag,'published live semantic plan',row)
            assert f.read(f.s['se_st_descriptor']+32,1)==bytes([f.get('se_mode',1)*2|f.get('se_l_mode',1)]),(tag,'mode-aware style identity')
        assert f.read(0xC600,1024)==f.shim
        frames.append(dict(render_CPU_instructions=f.total_instructions-instructions,leaf_rows=dll.gm_metric(0)-metrics[0],leaf_row_instructions=dll.gm_metric(1)-metrics[1],native8_cells=dll.gm_metric(2)-metrics[2],native8_instructions=dll.gm_metric(3)-metrics[3],tag=tag,mode=f.get('se_mode',1),width=[40,60,80][f.get('se_mode',1)],top=f.get('se_v_top'),pan=f.get('se_l_pan'),popup=rect))
        (out/'progress.json').write_text(json.dumps(dict(frames=frames),indent=2)+'\n')
    def finish_color(f,data,tag):
        sequence=f.get('se_e_draw_sequence',2)
        f.render()
        armed=f.get('se_e_draw_sequence',2)
        canonical,reu,catalog=f.canonical(),f.reu(),f.catalog()
        instructions=f.total_instructions;steps=f.idle_steps
        if f.get('se_st_request',1)==1:
            assert not f.get('se_st_valid',1)
            assert armed==sequence+(f.get('se_mode',1)==0)
            f.finish_style();assert f.get('se_e_draw_sequence',2)==armed+1
        else:
            assert f.get('se_st_valid',1) and armed==sequence+1
        check(f,data,tag,published=True)
        assert f.canonical()==canonical and f.reu_safe(reu,tag) and f.catalog()==catalog,(tag,'style mutated canonical/REU/catalog')
        # $8D00 is an inactive phase union once the persistent owner and lease
        # gates clear; its se_fs_owned alias is not ownership in owner0.
        assert f.get('se_doc_read_locks',1)==0 and f.get('se_f_owner',1)==0
        style_intervals.append(dict(tag=tag,CPU_instructions=f.total_instructions-instructions,idle_steps=f.idle_steps-steps))
    if colored:
        data=native_text('# *Heading* **strong**\rA *cyan* **yellow** ***pink*** @@code@@\r:::basic\r10PRINT"String":REM comment\r20 GOTO 10\r:::\r:::asm\rlabel: lda #$20 ; comment\r.byte 12,"Text"\r:::\r')
        f=fixture(data)
        try:
            for target in [1,2]:
                f.mode(96+target,target)
                finish_color(f,data,f'color-first-{target}-ready')
                assert len(set(f.read(0x4000+80,880)))>=5,'independent multicolor tile coverage'
            f.mode(96,0);finish_color(f,data,'color-return40-recolored')
            cases.append('independent mode-aware semantic pixels/inkvotes, headingreverse andfontrestore')
        finally:f.close()

    if colored:
        for target,width in [(1,60),(2,80)]:
            original=native_text('# *Heading* **strong** ***both***\rplain *x* **y** ***z*** @@q@@\r:::asm\rlabel: lda #$20 ; comment\r.byte "Text",1\r:::\r')
            f=fixture(original)
            try:
                f.mode(96+target,target);finish_color(f,original,f'color-{width}-tile-conflicts')
                # Real reversed selection overlaps heading reversal and a tile
                # boundary. Selection/caret invert once without recoloring ink.
                f.position(18);f.command(68)
                for _ in range(14):f.command(1)
                assert f.get('se_sel_anchor')>f.get('se_hot_caret')
                finish_color(f,original,f'color-{width}-heading-reverse-selection')
                f.command(50);position=original.index(native_text('Text'))+2;f.position(position);f.key(34)
                edited=original[:position]+b'"'+original[position:]
                assert f.get('se_hot_pending',1)
                finish_color(f,edited,f'color-{width}-pending-malformed-quote')
                assert f.get('se_hot_pending',1),'color planning must not flush pending gap'
                f.command(16);finish_color(f,original,f'color-{width}-quote-undo')
                f.command(17);finish_color(f,edited,f'color-{width}-quote-redo')
                f.command(77);finish_color(f,edited,f'color-{width}-nowrap')
                f.command(75);finish_color(f,edited,f'color-{width}-pan')
            finally:f.close()
        cases.append('bothnarrowwidths semanticcross-tile conflicts/headingselectionunion/pendingquote/undo/redo/nowrap/pan')
        # Tokens start beyond64KiB and straddle the lexical128-byte source
        # packet. A separate far closing delimiter must affect visible ink.
        prefix=native_text('prefix\r')*9400;opening=native_text(':::asm\r')
        line=native_text('label: '+(' '*120)+'lda #$1234 ; crosspacket token\r')
        data=prefix+opening+line+native_text(' .word label+1\r:::\r# After\r');body=len(prefix)+len(opening)
        assert body>65536 and line[127:130]==native_text('lda')
        f=fixture(data)
        try:
            f.position(body+127)
            for target,width in [(1,60),(2,80)]:
                f.mode(96+target,target);finish_color(f,data,f'color-{width}-offset24-wrap')
                if not f.get('se_l_mode',1):f.command(77)
                finish_color(f,data,f'color-{width}-offset24-nowrap')
                f.command(75);finish_color(f,data,f'color-{width}-offset24-manualpan')
                f.command(76)
        finally:f.close()
        data=native_text('*')+b'a'*66000+native_text('* closing\r# After\r');f=fixture(data)
        try:
            for target,width in [(1,60),(2,80)]:
                f.mode(96+target,target);finish_color(f,data,f'color-{width}-closer-beyond64KiB')
        finally:f.close()
        cases.append('24bitcodeanchors/cross128keyword/wrap/pan andinlinecloserbeyond64KiB')
        for target,width in [(1,60),(2,80)]:
            original=native_text(':::basic\r10 PRINT "')+b'A'*300+native_text('"\r20 GOTO 10\r:::\r')
            f=fixture(original)
            try:
                f.mode(96+target,target);position=len(native_text(':::basic\r'));f.position(position)
                f.begin_style();f.until_lexical(2)
                assert not f.call('se_doc_read_acquire').p&1
                f.queued(ord('Q'));f.tick()
                assert f.get('se_f_owner',1)==0 and not f.get('se_fs_owned',1) and not f.get('st_lex_phase',1)
                assert not f.get('se_st_busy',1) and f.get('se_doc_read_locks',1)==1
                edited=original[:position]+b'Q'+original[position:];assert f.merged()==edited
                assert not f.call('se_doc_read_release').p&1
                f.settle();finish_color(f,edited,f'color-{width}-activelexical-input-cancel')
            finally:f.close()
            for identity_,slot,phase,label in [(14,1,None,'missingC14'),(14,0,None,'missingR14'),(15,1,None,'missingC15initial'),(15,1,3,'missingC15paint')]:
                # A short token can now be painted inside one bounded C15 call,
                # so phase3 is not an idle-visible fault seam. Keep the late-C15
                # case honest with a comment span that must yield while painting.
                body=';'+('A'*160) if phase else 'label: lda #$1234 ; comment'
                data=native_text(':::asm\r'+body+'\r:::\r');f=fixture(data)
                try:
                    f.mode(96+target,target);f.begin_style()
                    if phase:f.until_lexical(phase)
                    assert not f.call('se_doc_read_acquire').p&1
                    f.remove(identity_,slot);canonical,reu,catalog=f.canonical(),f.reu(),f.catalog()
                    f.finish_style(False)
                    assert f.get('se_st_request',1)==0x80 and f.get('se_f_owner',1)==0
                    assert not f.get('se_fs_owned',1) and not f.get('st_lex_phase',1) and f.get('se_doc_read_locks',1)==1
                    assert f.canonical()==canonical,(width,label,'fault changed canonical')
                    assert f.reu_safe(reu,label)
                    assert f.catalog()==catalog,(width,label,'fault changed catalog')
                    check(f,data,f'color-{width}-{label}-fallback')
                    calls=f.get('se_overlay_calls',2)
                    for _ in range(4):f.tick()
                    assert f.get('se_overlay_calls',2)==calls,'same failedcontext retried overlay'
                    assert not f.call('se_doc_read_release').p&1
                finally:f.close()
        cases.append('bothnarrowwidths activeC15inputcancellation/missingC14/R14/C15 preservesforeignlease andplainfallback/request80')

    data=native_text('# Mixed CASE')+b'\r'+(native_text('A long line with 0123456789 and graphic ')+bytes([0xA1,0xFF]))*7+b'\r'+native_text('short\n'.replace('\n','\r'))*28
    f=fixture(data)
    try:
        check(f,data,'initial40')
        if colored:f.recolor();check(f,data,'initial40-colored')
        for cmd,target in [(97,1),(98,2),(96,0),(100,1),(101,0)]:f.mode(cmd,target);check(f,data,f'direct-{cmd}')
        if colored:f.recolor();check(f,data,'return40-recolored')
        for target in [1,2,0]:f.mode(96+target,target,'typed');check(f,data,f'typed-{target}')
        for target in [1,2]:f.mode(100,target,'F8');check(f,data,'F8'+str(target))
        f.mode(96,0);check(f,data,'F8-grid-reset40')
        f.mode(98,2);check(f,data,'CTRL-F8-grid-start80')
        for target in [1,0]:f.mode(100,target,'CTRL-F8');check(f,data,'CTRL-F8'+str(target))
        cases.append('actual direct/typed/F8/CTRL-F8 mode routes preservecanonical/fullREU/catalog')
    finally:f.close()
    # Exact-width CR/EOF and empty rows in each narrow mode.
    for width,target in [(60,1),(80,2)]:
        for size,cr in [(0,False),(width-1,True),(width,False),(width,True),(width+1,False)]:
            data=b'A'*size+(b'\r' if cr else b'');f=fixture(data)
            try:f.position(len(data));f.mode(96+target,target);check(f,data,f'width{width}-EOF{size}-CR{cr}')
            finally:f.close()
    cases.append('empty/CR/EOF/exactwidth source geometry')
    for width,target in [(60,1),(80,2)]:
        data=b'A'*2400;f=fixture(data)
        try:
            f.mode(96+target,target);check(f,data,f'navigation-base{width}')
            for command,caret,label in [(37,width,'down'),(39,22*width,'page-down'),
                (38,width,'page-up'),(41,width+40,'jump40forward'),(40,width,'jump40back'),
                (2,width+1,'right'),(36,1,'up')]:
                f.command(command);assert f.get('se_hot_caret')==caret,(width,label,f.get('se_hot_caret'),caret)
                check(f,data,f'navigation-{width}-{label}')
        finally:f.close()
    cases.append('actualnarrowwidth cursor/page21rows/jump40 source navigation')
    data=native_text('clipboard and pending source ')*12+b'\rTAIL';f=fixture(data)
    try:
        f.position(4);f.command(68)
        for _ in range(6):f.command(2)
        f.command(69);clip=data[4:10];f.command(50);f.position(30)
        inserted=native_text('XY')
        for b in inserted:f.key(b)
        data=data[:30]+inserted+data[30:];f.command(68)
        assert f.get('se_hot_pending',1)
        for target in [1,2,0]:f.mode(96+target,target);check(f,data,f'pending-selection-mode{target}')
        # Normal navigation may commit its pending packet. Its own policy is
        # separate from the mode-only no-flush guard just exercised above.
        for _ in range(3):f.command(1)
        assert f.get('se_sel_mark',1) and f.get('se_sel_anchor')>f.get('se_hot_caret')
        for target in [1,2,0]:f.mode(96+target,target);check(f,data,f'reversed-selection-mode{target}')
        f.command(50);p=f.get('se_hot_caret');f.command(71);pasted=data[:p]+clip+data[p:];check(f,pasted,'paste-after-modes')
        f.command(16);check(f,data,'paste-undo');f.command(17);check(f,pasted,'paste-redo')
        cases.append('pendinggap/no-flush/group/clipboard/selection plusactualpaste undo redo')
    finally:f.close()
    data=b'A'*66000+b'\rEND';f=fixture(data)
    try:
        f.position(65580);f.command(77);f.mode(97,1);check(f,data,'24bit-nowrap60');assert f.get('se_l_pan')==65580-59
        f.command(75);check(f,data,'manualpan60');f.mode(98,2);check(f,data,'24bit-nowrap80');assert f.get('se_l_pan')==65580-79
        cases.append('24bit logicalrow/autopan/manualpan withactualmodechanges')
    finally:f.close()
    data=native_text('# Popup source')+b'\r'+native_text('background body ') *160;f=fixture(data)
    try:
        f.mode(98,2)
        if colored:finish_color(f,data,'colored-popup-base80')
        else:check(f,data,'popup-base80')
        f.key(0x85);f.key(native_text('f')[0]);check(f,data,'File-menu80');f.key(3)
        f.key(0x8B);check(f,data,'help80');f.key(0x8B)
        f.key(0x88)
        for b in native_text('mode 60'):f.key(b)
        check(f,data,'commandprompt80');f.key(3)
        # Do not service the queued directory request: actual modal construction
        # and stateless painting are the intended CPU lane, no fake DOS calls.
        f.hold_file_transport=True
        f.put('se_e_key',15,1);f.put('se_e_mods',4,1);f.call('se_editor_input')
        assert f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3
        phase=f.read(0x8D00,1152)
        if colored:
            f.m.write(f.s['st_lex_phase'],3);phase=f.read(0x8D00,1152)
            f.call('se_style_input');f.call('se_style_idle')
            assert f.get('se_f_owner',1)==1 and f.read(0x8D00,1152)==phase
        check(f,data,'File-owner1-modal80',True);assert f.read(0x8D00,1152)==phase
        f.put('se_e_key',0x8B,1);f.put('se_e_mods',0,1);f.call('se_editor_input');phase=f.read(0x8D00,1152)
        check(f,data,'File-owner1-help80',True);assert f.read(0x8D00,1152)==phase
        cases.append('native8 Filemenu/help/commandprompt/Fileowner1 overlays withalloutsidepixels exact')
    finally:f.close()
    # Missing C16 or either initial leaf must refuse before mode/VIC/source.
    for identity_,slot,cmd in [(16,1,97),(17,0,97),(16,0,98)]:
        f=fixture(b'unchanged source\r')
        try:
            f.remove(identity_,slot);canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();vic=f.read(0xD000,0x40);bitmap=f.read(0x6000,8000);font=f.read(0x4800,2048)
            f.command(cmd,error=0x17)
            assert f.get('se_mode',1)==0 and f.get('se_v_columns',1)==0
            assert f.read(0xD000,0x40)==vic and f.read(0x6000,8000)==bitmap and f.read(0x4800,2048)==font
            assert f.canonical()==canonical and f.reu()==reu and f.catalog()==catalog
        finally:f.close()
    cases.append('initialmissingC16/R17/R16 leavesoldmode/VIC/font/source/REU')
    result=dict(status='passed',identity=identity,cases=cases,frames=frames,
        narrow_semantic_colors=colored,style_intervals=style_intervals,root_idle_steps=sum(f.idle_steps for f in instances),
        bitmap_pixels=sum(64000 for x in frames if x['mode']),attributes=sum(1000 for x in frames if x['mode']),
        peak_CPU_instructions=max(f.peak for f in instances),whole_REU_bytes=2*1024*1024,
        instruction_profile_scope='Actual linked leaf entry-to-RTS instruction counts including helpers; se_overlay_active is catalogindex+1. CPU counts, not emulated cycles.',
        cache_guard_intervals=sum(f.reu_guards for f in instances),cache_regions_allowed=[[0,22*240],[0x1500,0x1680]] if 'se_gc_handle' in instances[0].s else [],cache_bytes_allowed=5664 if 'se_gc_handle' in instances[0].s else 0,catalog_bytes=192,shim_bytes=1024,new_product_builds=0,
        actual_ROM_font_read_substitutions=sum(f.rom_reads for f in instances),
        file_phase_bytes_preserved=1152,file_DOS_service_calls=0,
        source_sha256=source_hashes,
        limits=[ROM_SEAM,'Actual CPU/root commands and pixels; no native/VIC/physical keyboard/readability claim.',
                'Narrow sparse semantic colors tested.' if colored else 'Narrow body semantic roles intentionally allnormal0 white; wide syntaxcolors/folds not claimed.',
                'File popup lane ends before its real DOS service; no host open/save replacement.'])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--colors',action='store_true');a=p.parse_args()
    if not a.run:print('Prepared only; no product CPU/build/native invocation.');return
    out=ROOT/'build/grid-modes'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    try:run(out,a.fixture,a.colors)
    except BaseException as error:(out/'failure.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n');raise


if __name__=='__main__':main()
