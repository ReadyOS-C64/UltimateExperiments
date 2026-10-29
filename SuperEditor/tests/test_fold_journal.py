"""Actual-source callbacks and checked logical-object fold edit journal.

Privatebuild only; frozen800 editor has no journal hooks. Tests explicitly call
newservice at the real callback boundary, keeping source edits/history actual.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,re,shutil,subprocess,sys
import test_grid_modes as g
from redraw_model import native_text
ROOT=g.ROOT;OUT=ROOT/'build/fold-journal';DEFAULT=ROOT/'build/fold-projection/20261025T004848243921Z/fixture'
def build(out,frozen):
    for name,src in [('journal',ROOT/'src/editor_fold/journal.s'),('state',ROOT/'src/editor_fold/journal-state.s')]:subprocess.run(['ca65','-g','-I',str(ROOT/'src'),'-o',str(out/f'{name}.o'),str(src)],check=True)
    subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(frozen/'build/editor-report.json'),'--output',str(out/'externals.s'),str(out/'journal.o'),str(out/'state.o')],check=True)
    subprocess.run(['ca65','-o',str(out/'externals.o'),str(out/'externals.s')],check=True)
    (out/'journal.cfg').write_text('''MEMORY { J:start=$E000,size=$2000,file="journal.bin",type=ro; V:start=$0E40,size=$000F,file="",type=rw; B:start=$0E60,size=$0005,file="",type=rw; }
SEGMENTS { FOLD_JOURNAL:load=J,type=ro,define=yes; VIEWSTATE:load=V,type=bss,define=yes; BSS:load=B,type=bss,define=yes; }
''')
    subprocess.run(['ld65','-C','journal.cfg','-m','journal.map','-Ln','journal.lbl','journal.o','state.o','externals.o'],cwd=out,check=True)
    return {n:int(v,16) for v,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(out/'journal.lbl').read_text())}

class Fixture(g.Fixture):
    def __init__(self,out,frozen,dll,syms):
        self.observe=False;self.callbacks=[];self.journal_symbols=syms;super().__init__(out,frozen,dll,True);self.s.update(syms);self.m.load(0xE000,(out/'journal.bin').read_bytes());self.m.load(0x0E40,bytes(15));self.m.load(0x0E60,bytes(5))
    def call(self,name,a=0):
        before=self.get('se_doc_generation',2) if self.observe else None;r=super().call(name,a)
        if before is not None and self.get('se_doc_generation',2)!=before:
            op='flush' if self.get('se_hot_phase',1)==2 else 'commit';self.observe=False
            try:self.journal(op)
            finally:self.observe=True
            self.callbacks.append(op)
        return r
    def journal(self,op,error=0):
        canonical=self.canonical();before,reu,shim=self.read(0,65536),self.reu(),self.read(0xC600,1024);r=self.call('se_ej_'+op)
        assert bool(r.p&1)==bool(error) and r.a==error,(op,error,r.a)
        assert self.canonical()==canonical,'observermodifiedcanonicalstate'
        assert self.read(0xC600,1024)==shim
        # Entire phase including foreign ownership/data and canonical roots,
        # hot cache, selection/history state are immutable during the observer.
        assert self.read(0x8D00,0xD00)==before[0x8D00:0x9A00],op
        assert self.read(self.s['se_doc_roots'],256)==before[self.s['se_doc_roots']:self.s['se_doc_roots']+256]
        assert self.read(0xC600,1024)==self.shim
        after=self.reu();want=bytearray(reu)
        token=self.read(self.s['se_ef_token'],5);idx=token[0]
        if self.m.read(self.s['object_owner']+idx)==0x46:
            banks=self.m.read(self.s['object_banks']+idx)
            if banks:
                logical=self.m.read(self.s['object_extents']+idx*16+banks-1);physical=self.m.read(self.s['se_reu_map']+logical);at=physical*65536+64512
                if not error and op in('local','commit'):
                    at+=before[self.s['se_ej_count']]*9;want[at:at+9]=after[at:at+9]
        assert after==want,(op,'nonjournalREUchanged')
        return r
    def rebuild(self):
        self.m.write(self.s['se_overlay_frame']+1,4)
        r=self.call('se_ef_dispatch',0);assert not r.p&1
        for _ in range(10000):
            if r.a==0:break
            r=self.call('se_ef_dispatch',1);assert not r.p&1
        assert r.a==0 and self.get('se_ef_valid',1) and not self.get('se_f_owner',1)
    def flush_real(self):
        self.observe=True;seen=len(self.callbacks);assert not self.call('se_hot_call',8).p&1
        for _ in range(1000):
            if not self.get('se_hot_phase',1):break
            if len(self.callbacks)>seen:self.call('se_hot_call',2);continue
            phase=self.get('se_h_phase',1)
            if phase==4 and self.get('se_hot_feed_left',2):self.call('se_hot_call',2)
            else:self.call('se_history_call',4)
        assert not self.get('se_hot_phase',1) and self.callbacks[seen:]==['flush']
    def records(self):
        self.journal('readlog');return self.read(0x8000,self.get('se_ej_count',1)*9)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fixture',type=Path,default=DEFAULT);args=ap.parse_args();out=OUT/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen=out/'fixture';shutil.copytree(args.fixture,frozen);identity=json.loads((frozen/'freeze.json').read_text());s=build(out,frozen)
    g.editor_fixture.ROOT=g.cpu_editor.ROOT=frozen;g.editor_fixture.NAMES=g.cpu_editor.NAMES=identity['names'];dll=g.runner(out);f=Fixture(out,frozen,dll,s);events=[]
    def event(p,d,i):return b''.join(x.to_bytes(3,'little') for x in [p,d,i])
    try:
        data=native_text('# First\rBody hidden\r# Tail\rlast\r');f.source(data);f.typed(native_text('fold'));f.journal('baseline');assert f.records()==b'';assert f.get('se_ej_status',1)==1
        for raw,deleted in [(ord('A'),0),(ord('B'),0),(None,1)]:
            at=f.get('se_hot_caret');f.put('se_hot_delete',deleted,1);f.journal('local');events.append(event(at,deleted,1-deleted))
            if raw is None:f.command(4)
            else:f.key(raw)
            assert f.records()==b''.join(events)
        assert f.get('se_ej_count',1)==3 and f.get('se_ej_ticket',4)==3 and f.get('se_ej_status',1)==2
        print('ACTUAL3APPENDS',events,flush=True)
        # Drive real packet/history steps, separating the actual commit from
        # C6 finalization exactly where the production C4 callback is placed.
        f.flush_real();assert f.get('se_ej_count',1)==3 and f.records()==b''.join(events)
        new=f.merged();before=f.get('se_ej_ticket',4);f.command(16)
        assert f.merged()==data and f.callbacks==['flush','commit'] and f.get('se_ej_ticket',4)==before+1
        events.append(f.read(f.s['se_doc_edit_position'],9));assert f.records()==b''.join(events)
        f.command(17);assert f.merged()==new;events.append(f.read(f.s['se_doc_edit_position'],9));assert f.records()==b''.join(events)
        # Rebuild/arm on an actual pending merged source, without flushing it.
        # Next local tuple is incremental from that freshly parsed snapshot.
        f.observe=False;f.put('se_hot_delete',0,1);f.journal('local');f.key(ord('C'))
        pending_source=f.merged();pending_generation=f.get('se_doc_generation',2);ticket=f.get('se_ej_ticket',4)
        f.rebuild();assert f.get('se_hot_pending',1) and f.merged()==pending_source and f.get('se_doc_generation',2)==pending_generation
        f.journal('baseline');assert f.records()==b'';assert f.get('se_ej_count',1)==0 and f.get('se_ej_ticket',4)==ticket and f.get('se_ej_length')==len(pending_source)
        at=f.get('se_hot_caret');f.put('se_hot_delete',0,1);f.journal('local');f.key(ord('D'))
        assert f.records()==event(at,0,1) and f.get('se_ej_ticket',4)==ticket+1
        count=f.get('se_ej_count',1);ticket=f.get('se_ej_ticket',4);f.flush_real();assert f.get('se_ej_count',1)==count and f.get('se_ej_ticket',4)==ticket
        # Foreign modal ownership/lease and phase bytes are neither inspected
        # nor released by this operation-sized observer.
        phase=f.read(0x8D00,1152);owner=f.get('se_f_owner',1);locks=f.get('se_doc_read_locks',1)
        f.m.load(0x8D00,bytes((i*31+7)&255 for i in range(1152)));f.put('se_f_owner',1,1);f.put('se_doc_read_locks',1,1)
        f.journal('readlog');assert f.get('se_f_owner',1)==1 and f.get('se_doc_read_locks',1)==1
        f.m.load(0x8D00,phase);f.put('se_f_owner',owner,1);f.put('se_doc_read_locks',locks,1)
        # A full journal disables retention before event113; the actual next
        # source edit is still allowed, matching the root wrapper contract.
        while f.get('se_ej_count',1)<112:
            f.put('se_hot_delete',0,1);f.journal('local');f.key(ord('E'))
        witness=f.read(f.s['se_ej_generation'],5)+f.read(f.s['se_ej_count'],1)+f.read(f.s['se_ej_ticket'],4)
        before=f.merged();position=f.get('se_hot_caret');f.put('se_hot_delete',0,1);f.journal('local',0xB7)
        assert f.get('se_ej_status',1)==0x80 and f.read(f.s['se_ej_generation'],5)+f.read(f.s['se_ej_count'],1)+f.read(f.s['se_ej_ticket'],4)==witness
        f.key(ord('Z'));assert f.merged()==before[:position]+b'Z'+before[position:]
        # Restore a fresh actual parser baseline before each independent guard.
        faults=[]
        for label in ['source-token','source-epoch','fold-token','fold-owner','overlap','capacity','generation','visiblelength','ticketwrap','dmawrite','dmaread']:
            f.rebuild();f.journal('baseline');restore=None
            if label=='source-token':at=f.s['se_ef_key'];restore=f.read(at,1);f.m.write(at,restore[0]^1);error=0xB7
            elif label=='source-epoch':at=f.s['se_ef_key']+24;restore=f.read(at,1);f.m.write(at,restore[0]^1);error=0xB7
            elif label=='fold-token':at=f.s['se_ef_token']+1;restore=f.read(at,1);f.m.write(at,restore[0]^1);error=0x31
            elif label=='fold-owner':
                token=f.read(f.s['se_ef_token'],5);logical=f.m.read(f.s['object_extents']+token[0]*16);at=f.s['se_reu_logical_owner']+logical;restore=f.read(at,1);f.m.write(at,0x45);error=0x34
            elif label=='overlap':at=f.s['se_ef_count'];restore=f.read(at,2);f.m.load(at,(2017).to_bytes(2,'little'));error=0xB7
            elif label=='capacity':at=f.s['se_ef_capacity_banks'];restore=f.read(at,1);f.m.write(at,2);error=0xB7
            elif label=='generation':at=f.s['se_ej_generation'];restore=f.read(at,2);f.m.load(at,(f.get('se_doc_generation',2)^1).to_bytes(2,'little'));error=0xB7
            elif label=='visiblelength':at=f.s['se_ej_length'];restore=f.read(at,3);f.m.load(at,(f.get('se_ej_length')+1).to_bytes(3,'little'));error=0xB7
            elif label=='ticketwrap':at=f.s['se_ej_ticket'];restore=f.read(at,4);f.m.load(at,bytes([255])*4);error=0xB7
            else:
                # Explicit JOURNAL-only callsite failure; real provider/DMA
                # implementations and all other calls remain unchanged.
                if label=='dmaread':f.put('se_hot_delete',0,1);f.journal('local');f.key(ord('F'))
                code=f.read(0xE000,len((out/'journal.bin').read_bytes()));pattern=b'\x20'+f.s['se_object_copy'].to_bytes(2,'little');sites=[0xE000+i for i in range(len(code)-2) if code[i:i+3]==pattern];assert len(sites)==2
                at=sites[0 if label=='dmawrite' else 1];restore=f.read(at,3);f.m.load(0x0E80,b'\xA9\x04\x38\x60');f.m.load(at+1,b'\x80\x0E');error=4
            count,tick,gen,length=f.get('se_ej_count',1),f.get('se_ej_ticket',4),f.get('se_ej_generation',2),f.get('se_ej_length')
            f.put('se_hot_delete',0,1);f.journal('readlog' if label=='dmaread' else 'local',error)
            assert f.get('se_ej_status',1)==0x80 and (f.get('se_ej_count',1),f.get('se_ej_ticket',4),f.get('se_ej_generation',2),f.get('se_ej_length'))==(count,tick,gen,length)
            f.m.load(at,restore);faults.append(label)
        # True24-bit positions and source lengths, using real canonical
        # history publication/replay and the same checked object journal.
        f.close();f=Fixture(out,frozen,dll,s)
        far=b'P'*65530+native_text('\r# Far\rbody here\r# End\r')
        f.source(far);f.put('se_ef_capacity_banks',2,1);f.typed(native_text('fold'));assert f.m.read(f.s['object_banks']+f.m.read(f.s['se_ef_token']))==2;f.position(65540);f.journal('baseline')
        f.put('se_hot_delete',0,1);f.journal('local');f.key(ord('X'));assert f.records()==event(65540,0,1)
        f.flush_real();assert f.get('se_ej_count',1)==1;farnew=f.merged()
        f.command(16);assert f.merged()==far;f.command(17);assert f.merged()==farnew
        assert f.records()==event(65540,0,1)+event(65540,1,0)+event(65540,0,1)
        assert f.get('se_ej_count',1)==3 and f.get('se_ej_generation',2)==f.get('se_doc_generation',2)
        result=dict(status='passed',identity=identity,code_bytes=len((out/'journal.bin').read_bytes()),view_bytes=15,bss_bytes=5,faults=faults,events=[list(int.from_bytes(e[i:i+3],'little') for i in [0,3,6]) for e in events],callbacks=f.callbacks)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:f.close()
if __name__=='__main__':main()
