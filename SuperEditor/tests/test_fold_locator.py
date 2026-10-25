"""Actualbounded fold target locator, independent nestedinterval oracle.

Builds only build/fold-locator. Actualfoundation, objects, checked REU DMA;
no editor/sharedbuild/VICE. Source canonicalbytes and everyREUbyte are immutable.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import ctypes as C,hashlib,json,random,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import test_folds as base
from peddle import Machine,VENDOR,library
OUT=ROOT/'build/fold-locator';OUT.mkdir(exist_ok=True)
SOURCES=['reu/provider','reu/dma','object/state','object/validate','object/allocate','object/resize','object/copy','fold/state','fold/store','fold/validate','fold/locate','fold/probe']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    cfg=OUT/'probe.cfg';cfg.write_text((ROOT/'src/fold/probe.cfg').read_text().replace('FOLD_QUERY:load=QUERY,type=ro,define=yes;','FOLD_LOCATE:load=QUERY,type=ro,define=yes;').replace(' FOLD_ACTION:load=ACTION,type=ro,define=yes;',''))
    objs=[]
    for n in SOURCES:
        p=OUT/(n.replace('/','-')+'.o');subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(p),str(ROOT/'src'/f'{n}.s')],check=True);objs.append(p)
    subprocess.run(['ld65','-C',str(cfg),'-o',str(OUT/'probe.bin'),'-m',str(OUT/'probe.map'),'-Ln',str(OUT/'probe.lbl'),*map(str,objs)],check=True)
    text=subprocess.check_output(['od65','--dump-segments',str(OUT/'fold-locate.o')],text=True);(OUT/'locate-segments.txt').write_text(text)
    measured={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',text,re.S)}
    assert measured['FOLD_LOCATE']<=450 and all(not measured[n] for n in ['CODE','RODATA','BSS','DATA','ZEROPAGE'])
    return measured

def runner():
    library();cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
static uint16_t copy_pc,tick_pc,read_pc;static uint64_t hits[4];
extern "C" void fl_config(uint16_t c,uint16_t t,uint16_t r){copy_pc=c;tick_pc=t;read_pc=r;}
extern "C" uint64_t fl_hit(int n){return hits[n];}
extern "C" uint64_t fl_run(ZeroPagePeddle*m){for(auto &n:hits)n=0;auto before=zeropage_peddle_regs(m).instructions;for(int i=0;i<50000;i++){auto r=zeropage_peddle_regs(m);if(r.pc==0x2ff)return r.instructions-before;if(r.pc==copy_pc){if(r.a<2)hits[r.a]++;}if(r.pc==tick_pc)hits[2]++;if(r.pc==read_pc)hits[3]++;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void fl_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,uint16_t(a+i));}
extern "C" void fl_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
    ext='.dylib' if sys.platform=='darwin' else '.so';p=OUT/('runner'+ext);subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(p)],check=True)
    d=C.CDLL(str(p));d.fl_config.argtypes=[C.c_uint16]*3;d.fl_run.argtypes=[C.c_void_p];d.fl_run.restype=C.c_uint64;d.fl_hit.argtypes=[C.c_int];d.fl_hit.restype=C.c_uint64;d.fl_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];d.fl_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return d

# Independent containinginterval/tree reasoning, not an assembler/preorder scan.
def target_model(folds,query,mode):
    hidden=[(i,f) for i,f in enumerate(folds) if f.flags&1 and f.hidden<=query<f.end]
    if hidden:
        i,f=min(hidden,key=lambda pair:pair[1].depth)
        return 65535 if mode==1 else i
    eligible=[(i,f) for i,f in enumerate(folds) if f.start<=query<f.end and (mode==0 or (mode==1)==(not bool(f.flags&1)))]
    return max(eligible,key=lambda pair:pair[1].depth)[0] if eligible else 65535

class Fixture(base.Fixture):
    def __init__(self,d):
        self.d=d;self.locator_calls=0;self.guard_calls=0;self.fetched_records=0;self.locator_peak=0
        base.OUT=OUT;super().__init__();self.d.fl_config(self.s['se_reu_copy'],self.s['se_fold_tick'],self.s['se_fold_read'])
    def ram(self,name,n):
        a=self.s[name] if isinstance(name,str) else name;b=C.create_string_buffer(n);self.d.fl_read(self.m.handle,a,n,b);return b.raw
    def reu_image(self):
        b=C.create_string_buffer(2*1024*1024);self.d.fl_reu(self.m.handle,len(b),b);return b.raw
    def object_bytes(self,id,length):
        image=self.reu_image();banks=self.banks(id)
        return b''.join(image[bank*65536:bank*65536+min(65536,max(0,length-i*65536))] for i,bank in enumerate(banks))
    def call(self,name,a=0,x=0,y=0):
        guarded=name.startswith('se_fold_locate_');before=self.ram(0,65536) if guarded else None
        for n,v in [('pc',self.s[name]),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',y)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
        self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.d.fl_run(self.m.handle);assert used,(name,'nonreturn',hex(self.m.regs().pc));r=self.m.regs();self.peak[name]=max(self.peak.get(name,0),used);self.calls[name]=self.calls.get(name,0)+1
        self.last_hits=[self.d.fl_hit(i) for i in range(4)]
        if guarded:
            after=self.ram(0,65536);want=bytearray(before)
            allowed=[(0x100,0x200),(self.s['se_fold_state'],self.s['se_fold_state']+self.s['se_fold_state_size']),(self.s['se_fold_record'],self.s['se_fold_record']+32),(self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_object_id'],self.s['copy_left']+2),(0xDF00,0xDF0B)]
            for lo,hi in allowed:want[lo:hi]=after[lo:hi]
            assert after==want,(name,'full64KiBguard',next((hex(i),b,c) for i,(b,c) in enumerate(zip(after,want)) if b!=c))
            assert self.last_hits[0]==0,'locator mustneverstash'
            assert self.last_hits[1]<=1 and self.last_hits[3]<=1,'locator read budget'
            self.fetched_records+=self.last_hits[1];self.locator_peak=max(self.locator_peak,used);self.guard_calls+=1
        return r
    def immutable_inputs(self):
        return self.ram('se_fold_token',28)+self.ram('se_fold_caret',3)+self.ram('se_fold_motion',4)+self.ram('se_fold_select_a',6)+self.ram('se_fold_query',4)
    def locate(self,folds,query,mode):
        self.put('se_fold_query',query,3);self.put('se_fold_mode',mode);self.put('se_fold_target',0xBEEF,2)
        canonical=self.immutable_inputs();reu=self.reu_image();assert not self.call('se_fold_locate_begin').p&1
        assert self.get('se_fold_target',2)==0xBEEF and self.get('se_fold_valid')==1
        steps=reads=0
        while self.get('se_fold_busy'):
            before=self.get('se_reu_dma_calls',2);r=self.call('se_fold_locate_step');assert not r.p&1
            transferred=(self.get('se_reu_dma_calls',2)-before)&65535;assert transferred==self.last_hits[1]<=1
            assert self.last_hits[2]==1
            reads+=transferred;steps+=1
            if self.get('se_fold_busy'):assert self.get('se_fold_target',2)==0xBEEF
            assert steps<=len(folds)+1
        expected=target_model(folds,query,mode);actual=self.get('se_fold_target',2);assert actual==expected,(query,mode,actual,expected,folds[:20])
        assert self.immutable_inputs()==canonical and self.reu_image()==reu
        assert self.get('se_fold_valid')==1 and self.get('se_fold_error')==0
        self.locator_calls+=1;return steps,reads

def main():
    measured=build();d=runner();f=Fixture(d);rng=random.Random(0xF01D10CA);queries=trees=faults=cancels=0;cases=[]
    try:
        examples=[[],[base.Fold(0,3,100003)],
            [base.Fold(0,2,120),base.Fold(5,7,40,0,1,2,level=0),base.Fold(10,12,30,1,2,3,level=0),base.Fold(50,53,100,0,1),base.Fold(120,125,200,kind=3,level=0)],
            [base.Fold(0,2,100),base.Fold(3,5,100,0,1),base.Fold(6,8,100,1,2,2,level=0)],
            [base.Fold(65530,65536,100000),base.Fold(100000,100001,100003,kind=3,level=0)],
            [base.Fold(0xFFFF00,0xFFFF10,0xFFFFFF)],
            [base.Fold(i*3,i*3+1,200-i*3,65535 if i==0 else i-1,i,kind=1+(i%3),level=1 if i%3==0 else 0) for i in range(16)]]
        for original in examples:
            length=max([x.end for x in original]+[100003]);count=len(original)
            masks=range(1<<count) if count<=5 else [0,(1<<count)-1,0xAAAA,0x5555]
            for mask in masks:
                folds=[replace(x,flags=(mask>>i)&1) for i,x in enumerate(original)];assert base.valid_model(folds,length) and f.validate(folds,length);trees+=1
                points={0,length,*[v for x in folds for v in [x.start,max(0,x.start-1),x.hidden-1,x.hidden,x.end-1,x.end]]}
                for q in sorted(points):
                    for mode in range(3):f.locate(folds,q,mode);queries+=1
        cases.append('nestedheadings/fences/regions,16deep, equalends, allcollapsecombinations,opener/body/end/EOF,24bit')
        for _ in range(40):
            folds=[base.Fold(0,3,500,flags=rng.randrange(2))]
            for j in range(rng.randrange(2,10)):
                start=5+j*45;parent=len(folds);kind=rng.randrange(1,4)
                folds.append(base.Fold(start,start+3,start+40,0,1,kind,flags=rng.randrange(2),level=1 if kind==1 else 0))
                if rng.randrange(2):folds.append(base.Fold(start+5,start+8,start+30,parent,2,3,flags=rng.randrange(2),level=0))
            assert base.valid_model(folds,100003) and f.validate(folds);trees+=1
            for _ in range(20):f.locate(folds,rng.randrange(501),rng.randrange(3));queries+=1
        cases.append('deterministicrandomlaminartrees independentlychooseeligiblevisibleinnermost')
        folds=[base.Fold(i*3,i*3+1,i*3+3,flags=i%2) for i in range(32768)]
        assert f.validate(folds);trees+=1
        large=[]
        for index,delta,mode in [(2047,0,0),(2048,1,2),(32767,0,0),(32767,1,2),(32767,3,0)]:
            n,r=f.locate(folds,index*3+delta,mode);queries+=1;large.append(dict(index=index,query=index*3+delta,mode=mode,steps=n,records=r,target=f.get('se_fold_target',2)))
        cases.append('actual1MiBrecordobject/noncontiguousbanks/index2047-2048/32767/endexclusive')
        small=[base.Fold(0,2,100),base.Fold(5,7,40,0,1),base.Fold(50,52,90,0,1)]
        # Readonlycancel leaves verifiedtree+unpublishedtarget intact. BusyBEGIN
        # andforeignjobCANCEL cannotsteal anotheroperation's frame.
        for stop in [0,1,2]:
            assert f.validate(small);f.put('se_fold_query',80,3);f.put('se_fold_mode',0);f.put('se_fold_target',0xBEAD,2);reu=f.reu_image();assert not f.call('se_fold_locate_begin').p&1
            for _ in range(stop):assert not f.call('se_fold_locate_step').p&1
            assert f.get('se_fold_busy');before=f.ram('se_fold_state',197);r=f.call('se_fold_locate_begin');assert r.p&1 and r.a==0xB2 and f.ram('se_fold_state',197)==before
            assert not f.call('se_fold_locate_cancel').p&1 and f.get('se_fold_error')==0xB3
            assert not f.get('se_fold_busy') and f.get('se_fold_valid')==1 and f.get('se_fold_target',2)==0xBEAD and f.reu_image()==reu
            assert not f.call('se_fold_locate_cancel').p&1;cancels+=1
        assert f.validate(small);f.put('se_fold_busy',1);f.put('se_fold_job',3);state=f.ram('se_fold_state',197);r=f.call('se_fold_locate_cancel');assert r.p&1 and r.a==0xB2 and f.ram('se_fold_state',197)==state;f.put('se_fold_busy',0)
        cases.append('cancel/idempotence/atomicoutput/foreignbusy ownership')
        # Eachidentity/input/mappingfault mustoccur beforeanotherDMA and never
        # publishpartialtarget ormodifya REUbyte. Revalidateaftereachfault.
        for field,width in [('se_fold_epoch',4),('se_fold_token',5),('se_fold_count',2),('se_fold_length',3),('se_fold_query',3),('se_fold_mode',1)]:
            assert f.validate(small);f.put('se_fold_query',80,3);f.put('se_fold_mode',0);f.put('se_fold_target',0xFACE,2);assert not f.call('se_fold_locate_begin').p&1;assert not f.call('se_fold_locate_step').p&1
            old=f.ram(field,width);f.put(field,int.from_bytes(old,'little')+1,width);reu=f.reu_image();dma=f.get('se_reu_dma_calls',2);r=f.call('se_fold_locate_step')
            assert r.p&1 and r.a==0xB1 and f.get('se_reu_dma_calls',2)==dma and f.reu_image()==reu
            assert f.get('se_fold_target',2)==0xFACE and not f.get('se_fold_busy') and not f.get('se_fold_valid');f.put(field,old);faults+=1
        for label,get_address in [('objectgeneration',lambda:f.s['object_gen_lo']+f.fold_id),('provider_epoch',lambda:f.s['se_reu_epoch']),('foreignlogicalowner',lambda:f.s['se_reu_logical_owner']+f.m.read(f.s['object_extents']+16*f.fold_id+15)),('foreignphysicalowner',lambda:f.s['se_reu_physical_owner']+f.fold_banks[-1])]:
            assert f.validate(small);f.put('se_fold_query',80,3);f.put('se_fold_mode',0);f.put('se_fold_target',0xFACE,2);assert not f.call('se_fold_locate_begin').p&1
            address=get_address();old=f.m.read(address);f.m.write(address,(old+1)&255);reu=f.reu_image();dma=f.get('se_reu_dma_calls',2);r=f.call('se_fold_locate_step')
            assert r.p&1 and f.get('se_reu_dma_calls',2)==dma and f.reu_image()==reu
            assert f.get('se_fold_target',2)==0xFACE and not f.get('se_fold_valid');f.m.write(address,old);faults+=1
        for mode,q in [(3,0),(255,0),(0,100004)]:
            assert f.validate(small);f.put('se_fold_query',q,3);f.put('se_fold_mode',mode);f.put('se_fold_target',0xFACE,2);reu=f.reu_image();dma=f.get('se_reu_dma_calls',2);r=f.call('se_fold_locate_begin')
            assert r.p&1 and r.a==0xB0 and f.get('se_fold_target',2)==0xFACE and f.get('se_reu_dma_calls',2)==dma and f.reu_image()==reu;faults+=1
        cases.append('changedquery/filter/source/token/count/length/provider/generation/foreignlastmap guards beforeDMA')
        # Capacity andcursoroverflow mustnotwraprecordoffset into earlierdata.
        for count,index in [(32769,0),(3,65535)]:
            assert f.validate(small);f.put('se_fold_query',80,3);f.put('se_fold_mode',0);f.put('se_fold_target',0xFACE,2)
            if count>32768:
                f.put('se_fold_count',count,2);f.put('se_fold_bound_count',count,2);name='se_fold_locate_begin'
            else:
                assert not f.call('se_fold_locate_begin').p&1;f.put('se_fold_index',index,2);name='se_fold_locate_step'
            dma=f.get('se_reu_dma_calls',2);reu=f.reu_image();r=f.call(name);assert r.p&1 and r.a==0xB0 and f.get('se_reu_dma_calls',2)==dma and f.reu_image()==reu and f.get('se_fold_target',2)==0xFACE;faults+=1
        f.safe()
        result=dict(status='passed',module_bytes=measured['FOLD_LOCATE'],caller_foundation_bytes=f.s['se_fold_state_size'],record_buffer_bytes=32,new_BSS=0,new_ZP=0,validated_trees=trees,queries=queries,actual_fetched_records=f.fetched_records,guarded_locator_calls=f.guard_calls,full_RAM_guard_bytes=65536,whole_REU_bytes_unchanged=2097152,source_canary_bytes=len(f.source),shim_bytes=1024,cancel_cases=cancels,guard_faults=faults,peak_locator_call_instructions=f.locator_peak,large=large,cases=cases,source_sha256={p:sha(ROOT/p) for p in ['src/fold/locate.s','src/fold/locate.inc','src/fold/api.inc','src/fold/state.s','src/fold/store.s','src/fold/validate.s','tests/test_fold_locator.py','tests/test_folds.py']},limits=['Actualfoundation/object/provider/DMA CPUproof; no editor/native/foldUI integration.','Existingfoundation has exclusivecaller ownership, no independentreadleasecounter; everySTEP authenticatescompleteobjecttoken/mappings/sourcebinding.','Source24bit positions arelogical; actual100003byte sourceobject is anunchangedcanary, notadocumentreaderclaim.'])
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as e:
        (OUT/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(OUT/'failure-c64.bin').write_bytes(f.ram(0,65536));raise
    finally:f.close()
if __name__=='__main__':main()
