"""Actual resident hooks and R19 journal admission on an immutable product.

Current C19 retention is deliberately outside this frozen increment. Baseline
is explicitly called through the public resident service after real C19 build.
No source mutation or callback is supplied by the host.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,re,shutil
import test_grid_modes as g
from redraw_model import native_text
ROOT=g.ROOT;DEFAULT=ROOT/'build/fold-journal-integration/20261025T011436904003Z/fixture'
def labels(path):return {n:int(v,16) for v,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',path.read_text())}
def tuple9(p,d,i):return b''.join(v.to_bytes(3,'little') for v in [p,d,i])
class Fixture(g.Fixture):
    def catalog(self):return self.read(self.s['se_overlay_ids'],self.s['image_crc_hi']+self.s['se_overlay_capacity']-self.s['se_overlay_ids'])
    def journal(self,op,error=0):
        canonical,reu,catalog,phase=self.canonical(),self.reu(),self.catalog(),self.read(0x8D00,1152)
        r=self.call('se_ef_journal_call',op);assert bool(r.p&1)==bool(error) and r.a==error,(op,error,r.a)
        assert self.canonical()==canonical,('canonical',op,next((i,a,b) for i,(a,b) in enumerate(zip(canonical,self.canonical())) if a!=b))
        assert self.catalog()==catalog,('catalog',op,next((i,a,b) for i,(a,b) in enumerate(zip(catalog,self.catalog())) if a!=b))
        assert self.read(0x8D00,1152)==phase,('phase',op)
        assert self.read(0xC600,1024)==self.shim,('shim',op)
        if op in(5,6) or error:assert self.reu()==reu,'readonly/failedjournalchangedREU'
        return r
    def records(self):self.journal(6);return self.read(0x8000,self.get('se_ej_count',1)*9)
    def baseline(self,data,physical=32):
        self.source(data,physical=physical);self.typed(native_text('fold'));assert self.get('se_ef_valid',1);self.journal(5);assert self.get('se_ej_status',1)==1 and not self.get('se_ej_count',1)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fixture',type=Path,default=DEFAULT);args=ap.parse_args();out=ROOT/'build/fold-journal-integration'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen=out/'fixture';shutil.copytree(args.fixture,frozen);identity=json.loads((frozen/'freeze.json').read_text())
    assert len(identity['names'])==24 and identity['catalog_capacity']==32
    g.editor_fixture.ROOT=g.cpu_editor.ROOT=frozen;g.editor_fixture.NAMES=g.cpu_editor.NAMES=identity['names'];dll=g.runner(out);cases=[];faults=[];f=None
    data=native_text('# First\rBody hidden\r# Tail\rlast\r')
    def case(label,physical=32):
        nonlocal f
        if f is not None:f.close()
        f=Fixture(out,frozen,dll,True);f.baseline(data,physical);return f
    def source(want,label):
        assert f.merged()==want and f.read(0xC600,1024)==f.shim and not f.get('se_e_error',1),label
        assert not f.get('se_doc_read_locks',1) and not f.get('se_f_owner',1)
        cases.append(dict(label=label,count=f.get('se_ej_count',1),ticket=f.get('se_ej_ticket',4),status=f.get('se_ej_status',1),length=len(want)))
    try:
        case('actual');expected=data;records=[]
        for raw,command,delete in [(ord('A'),None,0),(ord('B'),None,0),(None,3,1),(None,4,1)]:
            p=f.get('se_hot_caret')-(command==3);insert=0 if delete else 1
            reu=f.reu();generation=f.get('se_doc_generation',2);history=b''.join(f.read(f.s[n],w) for n,w in [('se_h_current',4),('se_h_counter',4),('se_h_end',2),('se_h_cursor',2)])
            if command:f.command(command)
            else:f.key(raw)
            after=f.reu();want=bytearray(reu);idx=f.m.read(f.s['se_ef_token']);banks=f.m.read(f.s['object_banks']+idx);logical=f.m.read(f.s['object_extents']+idx*16+banks-1);physical=f.m.read(f.s['se_reu_map']+logical);at=physical*65536+64512+len(records)*9;want[at:at+9]=after[at:at+9];assert after==want,'localnonjournalREUwrite'
            assert f.get('se_doc_generation',2)==generation and b''.join(f.read(f.s[n],w) for n,w in [('se_h_current',4),('se_h_counter',4),('se_h_end',2),('se_h_cursor',2)])==history
            expected=expected[:p]+(bytes([raw]) if insert else b'')+expected[p+delete:];records.append(tuple9(p,delete,insert))
            assert f.records()==b''.join(records);source(expected,'actual-local-'+str(len(records)))
        assert f.get('se_ej_count',1)==4 and f.get('se_ej_ticket',4)==4
        f.typed(native_text('top'));assert not f.get('se_hot_pending',1) and f.get('se_ej_generation',2)==f.get('se_doc_generation',2)
        assert f.records()==b''.join(records);source(expected,'actual-flush-no-double-log')
        new=expected;f.command(16);records.append(f.read(f.s['se_doc_edit_position'],9));assert f.records()==b''.join(records);source(data,'actual-undo-inverse')
        f.command(17);records.append(f.read(f.s['se_doc_edit_position'],9));assert f.records()==b''.join(records);source(new,'actual-redo-forward')
        print('ACTUALHOOKS7PASS',flush=True)
        # Limited physical provider still stores journal inside the fold object:
        # no observer allocation or bank reuse is needed for these key edits.
        case('limited-provider',12);f.key(ord('L'));assert f.records()==tuple9(0,0,1);source(b'L'+data,'12banks-local')
        # Optional observer failures are suppressed by real resident wrappers;
        # the editor accepts the canonical key and retains no stale witness.
        for label in ['missingR19','fold-owner','source-key','journal-write','journal-read']:
            case(label);count,ticket=f.get('se_ej_count',1),f.get('se_ej_ticket',4);restore=None
            if label=='missingR19':f.remove(19,0)
            elif label=='fold-owner':
                idx=f.m.read(f.s['se_ef_token']);logical=f.m.read(f.s['object_extents']+idx*16);at=f.s['se_reu_logical_owner']+logical;restore=f.read(at,1);f.m.write(at,0x45)
            elif label=='source-key':at=f.s['se_ef_key']+24;restore=f.read(at,1);f.m.write(at,restore[0]^1)
            else:
                if label=='journal-read':f.key(ord('R'));count,ticket=f.get('se_ej_count',1),f.get('se_ej_ticket',4)
                m=labels(frozen/'build/overlays/rangeio.lbl');start=m['append'] if label=='journal-write' else m['se_ej_readlog'];end=m['log_offset'] if label=='journal-write' else 0xA000+len(f.assets['rangeio'])-36
                pattern=b'\x20'+f.s['se_object_copy'].to_bytes(2,'little');sites=[i for i in range(start,end-2) if f.read(i,3)==pattern];assert len(sites)==1,(label,sites)
                at=sites[0];restore=f.read(at,3);f.m.load(0x0E80,b'\xA9\x04\x38\x60');f.m.load(at+1,b'\x80\x0E')
            reu=f.reu()
            if label=='journal-read':
                f.journal(6,4);assert f.get('se_ej_status',1)==0x80;before=f.merged();p=f.get('se_hot_caret');f.key(ord('Z'));source(before[:p]+b'Z'+before[p:],'readfault-edit-still-works')
            else:f.key(ord('Z'));source(b'Z'+data,label+'-edit-still-works')
            assert f.reu()==reu,(label,'failedobserverREUwrite')
            assert f.get('se_ej_status',1)==0x80 and f.get('se_ej_count',1)==count and f.get('se_ej_ticket',4)==ticket,label
            if restore is not None:f.m.load(at,restore)
            faults.append(label)
        result=dict(status='passed',identity=identity,cases=cases,faults=faults,limits=['Actual product resident/C6/C4/C5 hooks and sealedR19; manualbaselineviaresidentservice, C19retentionnotyetintegrated.','Journal-only explicitRAMcallsite faultstub is labeled; actual source/provider code unchanged.','CPU ROM read seam as existinggridfixture; no native/VIC/cycleclaim.'])
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');raise
    finally:
        if f is not None:f.close()
if __name__=='__main__':main()
