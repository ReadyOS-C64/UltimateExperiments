"""Paired PAL native whole-operation54/59 lexical-cache cost and correctness.

Actual immutable cohorts, real File/Open/IRQ setup, same public-input/render
PC/SP stopwatch seam. No substituted code/source/derived proofs; cycle numbers
are service completion costs with warp, not physical key latency.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,re,shutil,socket,subprocess,zipfile
import test_lexical_cache_vice as lexical
from test_lexical_cache_vice import timing,plain,capacity,Captured,vice_plan,ROOT
from d81_image import D81Image

CONTROL=ROOT/'build/grid-raw-integrated/20261026T081330656536Z/fixture'
CANDIDATE=ROOT/'build/capture-index-fixed/20261026T183928480377Z/fixture'


def free_ports():
    for port in(8300,*range(8400,8440)):
        with socket.socket()as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',port))


class Plan(lexical.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=8300
        p['global_defaults']['monitor_port_span']=1;return p


def scenario(e,cohort):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True
    n.lex_trace=lexical.lexer_trace(e);n.boot()
    expected=54 if cohort=='control54'else 59
    assert len(json.loads((e/'freeze.json').read_text())['catalog'])==expected
    for language in('basic','asm'):
        # Native8's intervening bypass cases ended in Markdown. The shortened
        # pair must retain that pre-OPEN state or ASM would build unmeasured.
        if language=='asm':n.typed(language+'-preopen-markdown','syntax markdown')
        data=lexical.document(language);n.open('open-'+language,(language+'doc').upper().encode())
        n.typed(language+'-baseline-markdown','syntax markdown')
        if language=='basic':n.typed(language+'-hires','mode hires')
        n.raw(language+'-baseline-idle',['delete',f'break exec ${n.idle_pc:04x} if {n.condition(0)}','x','delete'])
        n.memory(language+'-caps-before','se_render_caps',1)
        n.send(language+'-full-prompt',b'\x88'+timing.native.live.grid.native_text('syntax full'),ui=2)
        n.snapshot(language+'-before',data,3,2)
        n.measure(language+'-first',data,3,key=13,category='full-command-whole-operation')
        n.measurements[-1].update(language=language,caps=3,phase='first',cohort=cohort)
        n.measure(language+'-warm',data,3,full=True,category='forced-full-repaint-whole-operation')
        n.measurements[-1].update(language=language,caps=3,phase='warm',cohort=cohort)
    return n


def run_owned_plan(plan,out):
    """Unchanged compile/run/assert protocol; avoid duplicate ownedREU files."""
    path=out/'plan.yaml';path.write_text(json.dumps(plan,indent=2)+'\n')
    command=['dotnet','run','--no-build','--project',str(vice_plan.PROJECT),'--']
    for mode,extra in[('compile-plan',[]),('run-plan',['--close-vice','--no-tui'])]:
        p=subprocess.run(command+[mode,'--plan',str(path)]+extra,cwd=ROOT,capture_output=True,text=True,timeout=1200)
        (out/(mode+'.stdout.txt')).write_text(p.stdout);(out/(mode+'.stderr.txt')).write_text(p.stderr)
        if mode=='run-plan'and p.stdout.strip().startswith('{'):
            outcome=json.loads(p.stdout)
            if 'RunDir'in outcome and Path(outcome['RunDir']).exists():
                shutil.copytree(outcome['RunDir'],out/'run',copy_function=os.link)
        assert not p.returncode,(mode,p.stdout[-1800:],p.stderr[-1000:])
    manifest=json.loads(Path(outcome['Manifest']).read_text(encoding='utf-8-sig'));assert manifest['status']=='success',manifest
    for path in(out/'run/stages').glob('*/monitor_command.txt'):assert 'ERROR'not in path.read_text(encoding='utf-8-sig'),path
    return manifest


def canonical(f):
    return f.read(f.s['se_doc_roots'],512)+b''.join(f.read(f.s[name],width)for name,width in(
        ('se_doc_meta',15),('se_doc_length',3),('se_doc_generation',2),('se_h_current',4),
        ('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),
        ('se_clip_token',5),('se_clip_length',3),('se_bc_ticket',8),('se_bc_head',3),('se_bc_ring',96)))


def evaluate(n,cohort):
    original=timing.semantic.expected
    def expected(f,data,fonts):
        bits,attrs,rows=plain.expected(f,data,fonts,3);return bits,attrs,rows,None
    timing.semantic.expected=expected
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original
    images=timing.native.live.grid.reu_images(n.out/'run');trace=json.loads((n.e/'lexer-trace.json').read_text());records=[]
    for language in('basic','asm'):
        cap=n.out/'captures';before_id=language+'-before';before=images[before_id]
        before_ram=(cap/(before_id+'-ram.bin')).read_bytes();before_f=Captured(n.s,before_ram,(cap/(before_id+'-colors.bin')).read_bytes(),n.e)
        descriptor,lo,selected,oldroot=lexical.arena(n,before_ram,before);assert oldroot[31]==1
        source=canonical(before_f);retained=None
        for item in(x for x in result['measurements']if x['language']==language):
            ident=item['id'];ram=(cap/(ident+'-ram.bin')).read_bytes();reu=images[ident]
            f=Captured(n.s,ram,(cap/(ident+'-colors.bin')).read_bytes(),n.e)
            current,where,chosen,root=lexical.arena(n,ram,reu);assert current==descriptor and where==lo
            assert canonical(f)==source and f.get('se_render_caps',1)==3
            assert not f.get('se_hot_pending',1)and not f.get('se_sel_mark',1)and not f.get('se_h_dirty',1)
            workers={(g['slot'],g['id'])for g in item['cost_profile']['groups']}
            text=(n.out/('stopwatch-'+ident+'.log')).read_text(encoding='utf-8-sig')
            pcs=[int(x,16)for x in re.findall(r'(?m)^\.C:([0-9a-f]{4})\s',text,re.I)]
            counts={name:pcs.count(pc)for name,pc in trace['symbols'].items()}
            assert counts['entry']==sum(g['calls']for g in item['cost_profile']['groups']if(g['slot'],g['id'])==(1,25))
            wanted=bytearray(before)
            if cohort=='candidate59':
                assert root[31]==5 and root[98]==1 and f.get('se_bc_flags',1)&128
                assert not any(counts[k]for k in('se_sl_init','se_sl_feed','se_sl_finish'))
                assert (1,45)in workers
                if item['phase']=='first':
                    assert {(1,47),(1,49)}<=workers and chosen!=selected
                    assert reu[lo+selected:lo+selected+128]==before[lo+selected:lo+selected+128]
                    pages=[]
                    for page in range(1,16):
                        at=lo+256+page*8
                        if before[at:at+8]!=reu[at:at+8]:
                            assert before[at:at+8]==bytes(8);pages.append(page)
                            wanted[at:at+8]=reu[at:at+8];a=lo+page*4096;wanted[a:a+4096]=reu[a:a+4096]
                    assert len(pages)==2;wanted[lo+chosen:lo+chosen+128]=reu[lo+chosen:lo+chosen+128]
                    retained=reu[lo:lo+65536]
                else:
                    assert not workers&{(1,47),(1,49)}and reu[lo:lo+65536]==retained
                    wanted[lo:lo+65536]=retained
            else:
                assert root==oldroot and chosen==selected and reu[lo:lo+65536]==before[lo:lo+65536]
                assert all(counts[k]>0 for k in('se_sl_init','se_sl_feed','se_sl_finish')),'control must genuinely parse'
                assert not workers&{(1,45),(1,47),(1,49)}
            for bank in{b for raw in(before_ram,ram)for b in range(256)if raw[n.s['se_reu_physical_owner']+b]==0xfe}:
                assert ram[n.s['se_reu_physical_owner']+bank]in(0,0xfe)
                a=bank*65536;wanted[a:a+65536]=reu[a:a+65536]
            assert reu==wanted,(cohort,ident,'whole16MiB outside checkedCOW+actualFE')
            records.append(dict(cohort=cohort,id=ident,language=language,phase=item['phase'],cycles=item['emulated_cycles'],
                first_publish_cycles=item['first_publish_cycles'],counter_deltas=item['counter_deltas'],C25_trace=counts,
                bitmap_attrs_sha256=hashlib.sha256(ram[0x6000:0x7f40]+ram[0x4000:0x43e8]).hexdigest(),
                png_sha256=hashlib.sha256((n.out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
    assert(n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes();free_ports()
    summary=dict(status='PASS',cohort=cohort,identity=result['identity'],frames=records,native_pixels=result['native_pixels'],ports_released=True,visual_review='pending')
    (n.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary


def execute(source,cohort):
    free_ports();e=timing.freeze(source.resolve(),'pal');target=e.with_name(e.name.replace('display-timing-pal','lexical-cost-'+cohort));e.rename(target);e=target
    lexical.package(e);n=scenario(e,cohort);p=n.plan();assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in('tests','tools'):
            for path in(ROOT/folder).glob('*.py'):z.write(path,path.relative_to(ROOT))
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('LEXICAL_COST_NATIVE',cohort,e,flush=True);run_owned_plan(p,n.out);return e,evaluate(n,cohort)


def compare(paths):
    rows=[]
    for before,after in zip(paths[0][1]['frames'],paths[1][1]['frames']):
        assert(before['language'],before['phase'])==(after['language'],after['phase'])
        assert before['bitmap_attrs_sha256']==after['bitmap_attrs_sha256']and before['png_sha256']==after['png_sha256']
        rows.append(dict(id=before['id'],control_cycles=before['cycles'],candidate_cycles=after['cycles'],
            cycle_delta=after['cycles']-before['cycles'],percent_saved=100*(before['cycles']-after['cycles'])/before['cycles'],
            control_loads=before['counter_deltas']['se_overlay_loads'],candidate_loads=after['counter_deltas']['se_overlay_loads'],
            control_C25_feed=before['C25_trace']['se_sl_feed'],candidate_C25_feed=after['C25_trace']['se_sl_feed']))
    result=dict(status='PASS',scope=__doc__,cohorts={label:str(path)for label,(path,_)in zip(('control54','candidate59'),paths)},comparisons=rows,native_pixels=512000)
    out=paths[1][0]/'comparison.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--control',type=Path,default=CONTROL);p.add_argument('--candidate',type=Path,default=CANDIDATE)
    p.add_argument('--verify',type=Path,nargs=2,metavar=('CONTROL','CANDIDATE'));a=p.parse_args()
    if a.verify:
        import test_presentation_vice as presentation
        pairs=[(path.resolve(),evaluate(presentation.scenario_loaded(path.resolve()),label))for path,label in zip(a.verify,('control54','candidate59'))]
    else:pairs=[execute(source,label)for source,label in((a.control,'control54'),(a.candidate,'candidate59'))]
    compare(pairs)
