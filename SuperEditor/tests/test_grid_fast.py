"""Frozen actualroot cache/fast80 acceptance and old-vs-new instruction profile.

No sharedbuild/native. All expected pixels/roles/source packets derive canonical
source and independent models. Explicit fault injections affect cache callsites
or the rendering leaf only; source/provider implementations execute unchanged.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,sys,zipfile
import test_grid_modes as g
from redraw_model import Screen,verify_screen,native_text
ROOT=g.ROOT

def labels(p):return {x[2].lstrip('.'):int(x[1],16) for l in p.read_text().splitlines() if len(x:=l.split())==3 and x[0]=='al'}
def metrics(d):return [d.gm_metric(i) for i in range(4)]
def packets(f,data):
    width=[40,60,80][f.get('se_mode',1)];top=f.get('se_v_top');nowrap=f.get('se_l_mode',1);pan=f.get('se_l_pan') if nowrap else 0
    rows=g.row_starts(data,top,width,nowrap);plan=g.projected_plan(data,rows,width,pan) if f.get('se_st_valid',1) else bytes([1])*(width*22)
    lo,hi=sorted((f.get('se_hot_caret'),f.get('se_sel_anchor'))) if f.get('se_sel_mark',1) else (0,0);seen=False;result=[]
    for row,(start,stop) in enumerate(zip(rows,rows[1:])):
        end=stop-1 if stop>start and data[stop-1]==13 else stop;chars=[];roles=[];flags=[]
        for col in range(width):
            p=start+pan+col;style=plan[row*width+col] if p<end else 1;flag=1 if style&128 else 0
            chars.append(data[p] if p<end else 32);roles.append(g.semantic_role(style))
            if p<=end:
                if lo<=p<hi:flag|=2
                if p==f.get('se_hot_caret') and not seen:flag|=4;seen=True
            flags.append(flag)
        result.append((bytes(chars),bytes(roles),bytes(flags)))
    return result

def run_variant(out,previous,focused):
    frozen,identity=g.freeze(out,previous);g.editor_fixture.ROOT=g.cpu_editor.ROOT=frozen;g.editor_fixture.NAMES=g.cpu_editor.NAMES=identity['names'];dll=g.runner(out)
    frames=[];style_intervals=[];faults=[];instances=[]
    def fixture(data):
        f=g.Fixture(out,frozen,dll,True);f.source(data);instances.append(f);return f
    def check(f,data,tag,maximum=None,minimum=None,cache_complete=True,exact_dirty=False):
        f.logical=data;canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();before=f.total_instructions;tap=metrics(dll)
        f.render();wanted,anchors,seen,rect=g.expected(f,data)
        mode=f.get('se_mode',1)
        if mode:
            assert f.read(0x6000,8000)==wanted[0],(tag,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(f.read(0x6000,8000),wanted[0])) if a!=b))
            assert f.read(0x4000,1000)==wanted[1],(tag,'attributes')
        else:verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),Screen(*wanted,anchors,seen),tag=tag)
        actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
        assert actual==anchors,(tag,'anchors',actual,anchors)
        assert f.merged()==data and f.canonical()==canonical and f.catalog()==catalog and f.reu_safe(reu,tag)
        assert f.read(0xC600,1024)==f.shim
        value=dict(tag=tag,mode=mode,total_instructions=f.total_instructions-before,rows=dll.gm_metric(0)-tap[0],row_instructions=dll.gm_metric(1)-tap[1],native8_cells=dll.gm_metric(2)-tap[2],native8_instructions=dll.gm_metric(3)-tap[3],top=f.get('se_v_top'),pan=f.get('se_l_pan'))
        current_packets=packets(f,data) if mode else None
        if exact_dirty:
            previous_packets=getattr(f,'last_packets',None);assert previous_packets is not None and current_packets is not None
            dirty=sum(a!=b for a,b in zip(previous_packets,current_packets))
            assert value['rows']==dirty,(tag,'independentsemanticpacketdelta',value,dirty)
            value['independent_dirty_rows']=dirty
        f.last_packets=current_packets
        if maximum is not None:assert value['rows']<=maximum,(tag,'too manycomposedrows',value,maximum)
        if minimum is not None:assert value['rows']>=minimum,(tag,'missingcomposedrows',value,minimum)
        if cache_complete and mode and 'se_gc_handle' in f.s and f.get('se_gc_handle',1):
            handle=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+handle);valid=f.get('se_gc_valid')
            assert valid&0x3FFFFF==0x3FFFFF,(tag,'incompletecache afterpublishedframe',hex(valid))
            image=f.reu();width=[40,60,80][mode]
            for row,pieces in enumerate(packets(f,data)):
                for i,part in enumerate(pieces):
                    start=physical*65536+row*240+i*80
                    assert image[start:start+width]==part,(tag,'independentcachepacket',row,i)
        frames.append(value);(out/'progress.json').write_text(json.dumps(dict(frames=frames,faults=faults),indent=2)+'\n');return value
    def color(f,data,tag):
        f.render();canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();diag=f.read(0x8800,128);sel=f.read(f.s['se_sel_mark'],13);before=f.total_instructions;tap=metrics(dll);old_packets=packets(f,data)
        f.finish_style();assert f.canonical()==canonical and f.reu_safe(reu,tag) and f.catalog()==catalog
        assert f.read(0x8800,128)==diag and f.read(f.s['se_sel_mark'],13)==sel
        interval=dict(tag=tag,total_instructions=f.total_instructions-before,rows=dll.gm_metric(0)-tap[0],row_instructions=dll.gm_metric(1)-tap[1]);style_intervals.append(interval)
        if focused:
            dirty=sum(a!=b for a,b in zip(old_packets,packets(f,data)));assert interval['rows']==dirty,(tag,'stylepublicationsemanticpacketdelta',interval,dirty)
            interval['independent_dirty_rows']=dirty
        return check(f,data,tag,maximum=0 if focused else None)
    # Identical canonicalbytes and actualoperations on historical/currentbuilds.
    sample=native_text('# *Heading* **strong**\rplain *cyan* **yellow** ***pink*** @@code@@\r:::basic\r10PRINT"String":REM comment\r20 GOTO 10\r:::\r:::asm\rlabel: lda #$20 ; comment\r.byte 12,"Text"\r:::\r')
    for target,width in [(1,60),(2,80)]:
        f=fixture(sample)
        try:
            f.mode(96+target,target);check(f,sample,f'cold-full-{width}',minimum=22,maximum=22)
            check(f,sample,f'warm-plain-{width}',maximum=0 if focused else None)
            color(f,sample,f'warm-colored-{width}')
            f.command(2);check(f,sample,f'caret-same-row-{width}',maximum=1 if focused else None)
            check(f,sample,f'warm-caret-{width}',maximum=0 if focused else None)
        finally:f.close()
    if focused:
        for target,width in [(1,60),(2,80)]:
            data=b'A'*(width*5)+b'\r'+native_text('ordinary line source\r')*28;f=fixture(data)
            try:
                f.mode(96+target,target);f.position(width-1);check(f,data,f'edge-before-{width}',maximum=22)
                f.command(2);check(f,data,f'caret-cross-row-{width}',maximum=2,minimum=2)
                f.command(68);check(f,data,f'mark-empty-{width}',maximum=1)
                for _ in range(width+5):f.command(2)
                check(f,data,f'marked-region-{width}',maximum=3)
                f.command(1);check(f,data,f'marked-one-step-{width}',maximum=2)
                check(f,data,f'marked-unchanged-{width}',maximum=0)
                f.command(50);check(f,data,f'unmark-{width}',maximum=3)
                f.mode(96,0);check(f,data,f'mode40-font-{width}')
                f.mode(96+target,target);check(f,data,f'mode40-return-miss-{width}',minimum=22,maximum=22)
                # A popup covers bodytiles. Bothcurrent andprevious UI contexts
                # forcefull rows, includingrepair after an interruptedpopup.
                f.key(0x8B);check(f,data,f'help-open-{width}',minimum=22,maximum=22)
                check(f,data,f'help-still-open-{width}',minimum=22,maximum=22)
                f.key(0x8B);check(f,data,f'help-close-{width}',minimum=22,maximum=22)
                check(f,data,f'help-repaired-warm-{width}',maximum=0)
            finally:f.close()
            original=native_text('plain first line\rsecond *styled* line\r:::asm\rlabel: lda #$20 ; comment\r:::\r');f=fixture(original)
            try:
                f.mode(96+target,target);color(f,original,f'edit-baseline-colored-{width}')
                f.position(3);check(f,original,f'edit-position-{width}',maximum=1)
                f.key(ord('Q'));edited=original[:3]+b'Q'+original[3:];assert f.get('se_hot_pending',1)
                check(f,edited,f'pending-insert-{width}',exact_dirty=True)
                color(f,edited,f'pending-style-published-{width}');assert f.get('se_hot_pending',1)
                f.command(16);check(f,original,f'undo-source-{width}',exact_dirty=True);color(f,original,f'undo-style-{width}')
                f.command(17);check(f,edited,f'redo-source-{width}',exact_dirty=True);color(f,edited,f'redo-style-{width}')
            finally:f.close()
        # Allfaults below are isolated afterrealpublicrender/admission. The
        # original production source/provider functions are neverreplaced.
        data=native_text('fault source\r')*30
        f=fixture(data)
        try:
            f.mode(98,2);check(f,data,'faults-baseline',minimum=22);check(f,data,'faults-warm',maximum=0)
            sm=labels(frozen/'build/overlays/gridedit.lbl');payload=(frozen/'build/overlays/gridedit.seo').read_bytes()[36:]
            def site(start,end,target):
                pattern=b'\x20'+target.to_bytes(2,'little');a=start-0xB000;b=end-0xB000
                found=[0xB000+i for i in range(a,b-2) if payload[i:i+3]==pattern];assert len(found)==1,(start,end,found);return found[0]
            fetch=site(sm['se_grid_cache_row'],sm['se_grid_cache_commit'],f.s['se_reu_copy'])
            stash=site(sm['se_grid_cache_commit'],0xB000+len(payload),f.s['se_reu_copy'])
            alloc=site(sm['se_grid_cache_begin'],sm['se_grid_cache_invalidate'],f.s['se_reu_alloc'])
            f.m.load(0x0E40,b'\xA9\x04\x38\x60')
            for label,sites in [('cache-fetch-failure',[fetch]),('cache-stash-failure',[stash]),('cache-fetch-stash-failure',[fetch,stash])]:
                check(f,data,label+'-warm',maximum=0)
                if stash in sites:f.put('se_gc_valid',0)
                for at in sites:assert f.read(at,3)==b'\x20'+f.s['se_reu_copy'].to_bytes(2,'little');f.m.load(at+1,b'\x40\x0E')
                # A failedstash leaves validity clear, so omitpacketassertion
                # until realDMA has repairedthecache in thefollowingframe.
                record=check(f,data,label,minimum=22,maximum=22,cache_complete=stash not in sites)
                if stash in sites:assert f.get('se_gc_valid')==0
                for at in sites:f.m.load(at,payload[at-0xB000:at-0xB000+3])
                check(f,data,label+'-repair',minimum=22 if stash in sites else 0,maximum=22 if stash in sites else 0)
                check(f,data,label+'-repaired-warm',maximum=0);faults.append(dict(label=label,callsites=sites,render=record))
            # Cacheepoch mismatch must nottrust orfree theoldgraph; lazyBEGIN
            # may allocate a newFEbank, source/oldFEbytes remainunchanged.
            oldhandle=f.get('se_gc_handle',1);oldphysical=f.m.read(f.s['se_reu_map']+oldhandle);oldbank=f.reu()[oldphysical*65536:(oldphysical+1)*65536]
            f.put('se_gc_epoch',f.get('se_gc_epoch',2)^1,2)
            check(f,data,'cache-epoch-mismatch',minimum=22,maximum=22)
            assert f.get('se_gc_handle',1)!=oldhandle and f.m.read(f.s['se_reu_map']+oldhandle)==oldphysical
            assert f.reu()[oldphysical*65536:(oldphysical+1)*65536]==oldbank
            faults.append(dict(label='cacheepoch replacement leavesoldownedbank untouched'))
            # Only cacheBEGIN's allocatorcall is faulted; document allocator and
            # readers remain actual. ExistingFEbank is deliberatelyabandoned.
            f.put('se_gc_handle',0,1);f.m.load(alloc+1,b'\x40\x0E');record=check(f,data,'cache-allocator-failure',minimum=22,maximum=22)
            assert f.get('se_gc_handle',1)==0
            f.m.load(alloc,payload[alloc-0xB000:alloc-0xB000+3]);check(f,data,'cache-allocator-repair',minimum=22,maximum=22);check(f,data,'cache-allocator-warm',maximum=0)
            faults.append(dict(label='cacheallocator fault/fullrender fallback',render=record))
            # A missingcheckedleaf must failbeforebodypixels/cachepublication.
            at=f.remove(16,0);cache=f.read(f.s['se_gc_handle'],9);bits=f.read(0x6000,8000);attrs=f.read(0x4000,1000);seq=f.get('se_e_draw_sequence',2);canonical,reu=f.canonical(),f.reu()
            r=f.call('se_editor_render');assert r.p&1 and f.get('se_e_error',1)==0x17
            assert f.read(f.s['se_gc_handle'],9)==cache and f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.get('se_e_draw_sequence',2)==seq
            assert f.canonical()==canonical and f.reu()==reu
            f.m.write(f.s['se_overlay_ids']+at,16);f.put('se_e_error',0,1);check(f,data,'missing-leaf-recovered',maximum=0)
            faults.append(dict(label='missingR16 nofalsehit/nopixel/cachepublication'))
            # Render a realpopup, then abortits nextbodyrepair on thethirdleaf
            # call. This leavespart ofoldpopup damaged and mustnotpublish a
            # frame orcachevalidity for thefailedrow. Only theleafentry is
            # redirected toanexplicitcounted faulttrampoline in coldscratch.
            f.key(0x8B);check(f,data,'interrupt-help-complete',minimum=22,maximum=22)
            leaf=labels(frozen/'build/overlays/grid80.lbl')['se_narrow_row'];saved=f.read(leaf,4)
            assert saved[0]==0x86 and saved[2]==0x84
            stub=b'\xEE\x70\x0E\xAD\x70\x0E\xC9\x03\xD0\x04\xA9\x90\x38\x60'+saved+b'\x4C'+(leaf+4).to_bytes(2,'little')
            f.m.load(0x0E40,stub);f.m.write(0x0E70,0);f.m.load(leaf,b'\x4C\x40\x0E')
            canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();seq=f.get('se_e_draw_sequence',2);tap=metrics(dll)
            r=f.call('se_editor_render')
            assert r.p&1 and f.get('se_e_error',1)==0x90 and f.m.read(0x0E70)==3
            assert f.get('se_e_draw_sequence',2)==seq and f.get('se_gc_valid')==3
            assert f.get('se_gc_current_ui',1)==1 and f.get('se_gc_previous_ui',1)==1
            assert f.canonical()==canonical and f.catalog()==catalog and f.reu_safe(reu,'interruptedpopup')
            assert dll.gm_metric(0)-tap[0]==3
            f.m.load(leaf,saved);f.key(0x8B)
            check(f,data,'interrupted-help-close-repair',minimum=22,maximum=22)
            check(f,data,'interrupted-help-repaired-warm',maximum=0)
            faults.append(dict(label='thirdrowleaf fault afterrealpopup; only2successfulcachecommits andnopublication; fullclose repair',leaf=leaf,cold_trampoline=0x0E40))
            # A cachelogical/physical ownershipchange is neverborrowed orfreed.
            # Onlythose derivedtokenfields are faulted; documentownershipstays
            # intact. The realallocator selects anotherownedFEpair lazily.
            for kind in ['logical','physical']:
                oldhandle=f.get('se_gc_handle',1);oldphysical=f.m.read(f.s['se_reu_map']+oldhandle)
                address=f.s['se_reu_logical_owner']+oldhandle if kind=='logical' else f.s['se_reu_physical_owner']+oldphysical
                f.m.write(address,5);oldbank=f.reu()[oldphysical*65536:(oldphysical+1)*65536]
                check(f,data,'cache-'+kind+'-owner-mismatch',minimum=22,maximum=22)
                assert f.m.read(address)==5 and f.get('se_gc_handle',1)!=oldhandle
                assert f.m.read(f.s['se_reu_map']+oldhandle)==oldphysical
                assert f.reu()[oldphysical*65536:(oldphysical+1)*65536]==oldbank
                check(f,data,'cache-'+kind+'-owner-repaired-warm',maximum=0)
                faults.append(dict(label=kind+'owner replacement leavesforeignmetadata/oldbank untouched'))
        finally:f.close()
    result=dict(status='passed',identity=identity,frames=frames,style_intervals=style_intervals,faults=faults,REUbytes=2097152,derived_cache_allowed_bytes=5280 if focused else 0,cache_guards=sum(f.reu_guards for f in instances),limits=[g.ROM_SEAM,'CPU instruction accounting only; no nativecycles/VIC/readability/physicalkeyboardclaim.','Explicit private cachecallsite faultstubs are labeled; ordinary source/provider/DMA semantics execute unchanged.'])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    a=argparse.ArgumentParser();a.add_argument('--fixture',type=Path,required=True);a.add_argument('--baseline',type=Path,required=True);args=a.parse_args()
    out=ROOT/'build/grid-fast'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    with zipfile.ZipFile(out/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in [Path(__file__),Path(g.__file__),ROOT/'tools/peddle.py',ROOT/'tools/cpu_editor.py',ROOT/'tools/editor_fixture.py',ROOT/'tools/redraw_model.py',ROOT/'tools/supermark_model.py',ROOT/'tests/test_style_editor.py']:z.write(p,p.relative_to(ROOT))
    try:
        results={}
        for name,path,focused in [('baseline',args.baseline,False),('current',args.fixture,True)]:
            d=out/name;d.mkdir();results[name]=run_variant(d,path,focused)
        b={x['tag']:x for x in results['baseline']['frames']};c={x['tag']:x for x in results['current']['frames']};comparison={k:dict(old=b[k]['total_instructions'],new=c[k]['total_instructions'],oldrows=b[k]['rows'],newrows=c[k]['rows']) for k in b}
        (out/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n');print(json.dumps(dict(status='passed',output=str(out),comparison=comparison),indent=2))
    except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');raise
if __name__=='__main__':main()
