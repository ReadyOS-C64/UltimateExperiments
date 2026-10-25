"""Pure canonical-edit evidence checker plus actual frozen editor provenance.

Only isolated build/editor-fold-change; no sharedmake/production hooks. The
publication observer is explicit host instrumentation at actual successful
commits, NOT an existing durable product mutation ticket.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,hashlib,random,re,shutil,subprocess,sys
import test_grid_modes as g
from peddle import Machine
from redraw_model import native_text
ROOT=g.ROOT;OUT=ROOT/'build/editor-fold-change'
DEFAULT=ROOT/'build/fold-projection/20261025T004848243921Z/fixture'
OFF=dict(old=0,current=28,original=56,append=61,generation=66,epoch=68,ready=70,pending=71,phase=72,fault=73,base=74,oldlength=77,length=79,left=81,right=83,prefix=85,suffix=87,doclength=89,busy=92,kind=93,request=94,beforeticket=103,afterticket=107,auth=111,result=112,scratch=121,valid=127)

def put(frame,at,v,n):frame[at:at+n]=v.to_bytes(n,'little')
def number(b):return int.from_bytes(b,'little')
def build(out):
    (out/'helper.cfg').write_text('MEMORY { CODE:start=$1000,size=$1800,file="helper.bin",type=ro; }\nSEGMENTS { FOLD_CHANGE:load=CODE,type=ro,define=yes; }\n')
    (out/'externals.s').write_text('.export se_ef_change_frame\nse_ef_change_frame=$8D00\n')
    for name,src in [('helper',ROOT/'src/editor_fold/change-key.s'),('externals',out/'externals.s')]:subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(out/f'{name}.o'),str(src)],check=True)
    subprocess.run(['ld65','-C','helper.cfg','-m','helper.map','-Ln','helper.lbl','helper.o','externals.o'],cwd=out,check=True)
    syms={n:int(v,16) for v,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(out/'helper.lbl').read_text())};return syms

def key(f,committed=False):
    if not committed:
        assert not f.call('se_view_init').p&1
        for name in ['se_doc_meta','se_doc_original','se_doc_append']:
            f.m.load(f.s['se_object_id'],f.read(f.s[name],5));assert not f.call('se_object_validate').p&1
    return b''.join(f.read(f.s[n],w) for n,w in [('se_doc_meta',5),('se_doc_original',5),('se_doc_append',5),('se_doc_generation',2),('se_r_revision',4),('se_doc_length' if committed else 'se_v_length',3),('se_reu_epoch',2),('se_doc_epoch',2)])

def inputs(f,old,current):
    b=bytearray(128);b[:28]=old;b[28:56]=current
    for n,target,width in [('original','original',5),('append','append',5),('generation','generation',2),('epoch','epoch',2),('ready','ready',1),('pending','pending',1),('phase','phase',1),('fault','fault',1),('base','base',3),('old_length','oldlength',2),('length','length',2),('left','left',2),('right','right',2),('prefix','prefix',2),('suffix','suffix',2)]:b[OFF[target]:OFF[target]+width]=f.read(f.s['se_hot_'+n],width)
    b[89:92]=f.read(f.s['se_doc_length'],3);b[92]=f.get('se_doc_busy',1);b[111]=0xA5;b[112:121]=b'UNCHANGED';return b

class Checker:
    def __init__(self,out,s):
        self.s=s;self.m=Machine();self.m.load(0x1000,(out/'helper.bin').read_bytes());self.calls=0;self.peak=0
    def read_all(self):
        b=C.create_string_buffer(65536);self.dll.gm_read(self.m.handle,0,65536,b);return b.raw
    def run(self,b,entry,error=0):
        self.m.load(0x8D00,b);before=self.read_all();r,n=self.m.call(self.s['se_ef_change_'+entry]);after=self.read_all();self.calls+=1;self.peak=max(self.peak,n)
        want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];want[0x8D00+121:0x8D80]=after[0x8D00+121:0x8D80]
        if not error:want[0x8D00+112:0x8D00+121]=after[0x8D00+112:0x8D00+121]
        assert after==want,'full64KiB/input/result atomicity'
        assert bool(r.p&1)==bool(error) and r.a==error,(entry,error,r.a,r.p,b.hex())
        assert after[0x8D7F]==(not error)
        return tuple(number(after[0x8D70+i:0x8D73+i]) for i in [0,3,6])

class Fixture(g.Fixture):
    def __init__(self,*args):self.events=[];self.observe=False;super().__init__(*args)
    def call(self,n,a=0):
        before=key(self,True) if self.observe else None
        r=super().call(n,a)
        if before is not None:
            after=key(self,True)
            if before[15:17]!=after[15:17]:
                assert number(after[15:17])==number(before[15:17])+1
                self.events.append(dict(before=before,after=after,request=self.read(self.s['se_doc_edit_position'],9),service=n))
        return r

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fixture',type=Path,default=DEFAULT);args=ap.parse_args();out=OUT/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    syms=build(out);checker=Checker(out,syms);frozen=out/'fixture';shutil.copytree(args.fixture,frozen);identity=json.loads((frozen/'freeze.json').read_text());g.editor_fixture.ROOT=g.cpu_editor.ROOT=frozen;g.editor_fixture.NAMES=g.cpu_editor.NAMES=identity['names'];dll=g.runner(out);checker.dll=dll;cases=[]
    def pending(f,baseline,old,label):
        current=key(f);b=inputs(f,old,current);position,delete,insert=checker.run(b,'pending');actual=f.merged();assert baseline[:position]+actual[position:position+insert]+baseline[position+delete:]==actual,(label,position,delete,insert)
        cases.append(dict(label=label,kind='pending',tuple=[position,delete,insert],length=len(actual)));return b
    def published(f,baseline,old,label,kind):
        assert len(f.events)==1,(label,len(f.events));event=f.events.pop();current=key(f);b=inputs(f,old,current);b[93]=kind;b[94:103]=event['request'];put(b,103,100,4);put(b,107,101,4)
        position,delete,insert=checker.run(b,'publication');actual=f.merged();assert baseline[:position]+actual[position:position+insert]+baseline[position+delete:]==actual,(label,position,delete,insert)
        cases.append(dict(label=label,kind='publication',tuple=[position,delete,insert],observed_service=event['service']));return b
    f=Fixture(out,frozen,dll,True)
    try:
        data=native_text('# First\rBody text\r# Tail\rlast\r');f.source(data);f.position(10);old=key(f);f.observe=True
        for raw,label in [(ord('A'),'insertA'),(ord('B'),'insertB'),(0x14,'backspaceB'),(13,'insertCR')]:
            f.key(raw);last=pending(f,data,old,label)
        f.command(4);last=pending(f,data,old,'forwarddelete')
        changed=f.merged();assert not f.events,'pending keys must not commit'
        f.typed(native_text('top'));pub=published(f,data,old,'flush-aggregate',1);assert not f.get('se_hot_pending',1)
        old=key(f);f.command(16);undo=published(f,changed,old,'undo-real-inverse',3);assert f.merged()==data
        old=key(f);f.command(17);redo=published(f,data,old,'redo-real-forward',4);assert f.merged()==changed
        # Missing provenance must refuse stale request fields even when lengths
        # and generation happen to look plausible.
        faults=0
        for entry,b in [('pending',last),('publication',pub),('publication',undo),('publication',redo)]:
            for at in [0,5,10,24,26]:
                bad=bytearray(b);bad[at]^=1;checker.run(bad,entry,0xB7);faults+=1
            bad=bytearray(b);bad[111]=0;checker.run(bad,entry,0xB9);faults+=1
        for at in [103,107]:
            bad=bytearray(pub);bad[at]^=2;checker.run(bad,'publication',0xB9);faults+=1
        bad=bytearray(pub);put(bad,94,len(data)+1,3);checker.run(bad,'publication',0xB8);faults+=1
        bad=bytearray(last);put(bad,83,2049,2);checker.run(bad,'pending',0xB8);faults+=1
        # Real service behavior beyond64KiB, including an aggregate that
        # removes and inserts CR bytes, followed by actual journal replay.
        f.close();f=Fixture(out,frozen,dll,True)
        far=b'P'*65530+native_text('# Far\rbody here\r# End\r')
        f.source(far);f.position(65540);old=key(f);f.observe=True
        for raw in [ord('X'),13,ord('Y')]:f.key(raw);farframe=pending(f,far,old,'24bit-pending-'+str(raw))
        farnew=f.merged();f.typed(native_text('top'));farpublication=published(f,far,old,'24bit-flush',1)
        old=key(f);f.command(16);published(f,farnew,old,'24bit-undo',3);assert f.merged()==far
        old=key(f);f.command(17);published(f,far,old,'24bit-redo',4);assert f.merged()==farnew
        # Real block cut/paste use different producers from pending C6 edits.
        f.close();f=Fixture(out,frozen,dll,True);block=native_text('0123456789\r# Tail\r')
        f.source(block);f.position(2);f.command(68);f.position(7);old=key(f);f.observe=True
        f.command(69);assert not f.events
        f.command(70);cut=published(f,block,old,'block-cut',2);cutsource=f.merged();assert cutsource==block[:2]+block[7:]
        old=key(f);f.command(71);published(f,cutsource,old,'block-paste',2);assert f.merged()==block
        # Numeric/frame oracle independent of assembler subtraction/carry paths.
        rng=random.Random(0x6502F01D);randomized=0
        for i in range(1200):
            b=bytearray(last);oldlen=rng.randrange(2049);prefix=rng.randrange(oldlen+1);suffix=rng.randrange(oldlen-prefix+1)
            inserted=rng.randrange(2048-prefix-suffix+1);newlen=prefix+inserted+suffix
            base=rng.choice([0,65500,65536,0xFF0000,rng.randrange(0xF00000)]);total=min(0xFFFFFF,base+oldlen+rng.randrange(128))
            if total-oldlen+newlen>0xFFFFFF:continue
            put(b,21,total,3);put(b,49,total-oldlen+newlen,3);put(b,89,total,3);put(b,74,base,3)
            for at,v in [(77,oldlen),(79,newlen),(81,prefix),(83,2048-(newlen-prefix)),(85,prefix),(87,suffix)]:put(b,at,v,2)
            got=checker.run(b,'pending');assert got==(base+prefix,oldlen-prefix-suffix,inserted);randomized+=1
            # Same exact tuple as a witnessed committed publication, including
            # byte carries in generation/ticket and24-bit document lengths.
            c=bytearray(pub);c[:28]=b[:28];c[28:56]=b[28:56]
            generation=rng.randrange(65535);put(c,15,generation,2);put(c,43,generation+1,2)
            ticket=rng.randrange(0xFFFFFFFF);put(c,103,ticket,4);put(c,107,ticket+1,4)
            for j,v in enumerate(got):put(c,94+j*3,v,3)
            c[89:92]=c[49:52];c[93]=rng.randrange(1,5)
            assert checker.run(c,'publication')==got;randomized+=1
        for ticket in [0,0xFE,0xFF,0xFFFF,0xFFFFFF,0xFFFFFFFE]:
            c=bytearray(pub);put(c,103,ticket,4);put(c,107,ticket+1,4)
            assert checker.run(c,'publication')==tuple(number(pub[94+i:97+i]) for i in [0,3,6]);randomized+=1
        # Explicit alias/overflow/no-witness failures must not publish a tuple.
        for entry,b,changes,error in [
            ('pending',last,[(45,number(last[17:21]),4)],0xB7),
            ('pending',last,[(83,2049,2)],0xB8),
            ('pending',last,[(85,2048,2),(87,2048,2)],0xB8),
            ('pending',last,[(74,0xFFFFFF,3)],0xB8),
            ('publication',pub,[(15,65535,2),(43,0,2)],0xB7),
            ('publication',pub,[(103,0xFFFFFFFF,4),(107,0,4)],0xB9),
            ('publication',pub,[(94,0xFFFFFF,3),(97,2,3)],0xB8),
            ('publication',pub,[(100,0xFFFFFF,3)],0xB8),
            ('publication',pub,[(93,0,1)],0xB9),
            ('publication',pub,[(93,5,1)],0xB9)]:
            bad=bytearray(b)
            for at,value,width in changes:put(bad,at,value,width)
            checker.run(bad,entry,error);faults+=1
        helper_reu=C.create_string_buffer(2*1024*1024);dll.gm_reu(checker.m.handle,len(helper_reu),helper_reu);assert not any(helper_reu.raw),'purehelpermustnotmutateREU'
        result=dict(status='passed',identity=identity,code_bytes=len((out/'helper.bin').read_bytes()),caller_frame_bytes=128,resident_bss=0,zeropage=0,cases=cases,faults=faults,randomized=randomized,calls=checker.calls,peak_instructions=checker.peak,limits=['Publication serial is host observer evidence, absent from current production; no automatic integration claim.','No native/VIC timing claim.'])
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:f.close();checker.m.close()
if __name__=='__main__':main()
