"""Native actual59 automatic BASIC/ASM cache construction and warm reuse.

Real D81/ROM FileOpen and IRQ preset setup. Measurements use the disclosed
PC/SP/public-input seam. No parser result, root, reference or verification-bit
seed. Native pixels/source/catalog/stack/shim and actual retained53 are checked.
"""
from pathlib import Path
import argparse,binascii,hashlib,json,re,shutil,subprocess,sys,zipfile
import test_grid_plain_caret_vice as caret
import test_plain_geos as plain
from test_grid_plain_caret_vice import timing,capacity,ROOT,Captured,vice_plan
from d81_image import D81Image


def lexer_trace(e):
    """Rebuild only C25 from frozen sources; no product substitution."""
    out=e/'lexer-proof';out.mkdir()
    with zipfile.ZipFile(e/'product-sources.zip')as z:
        for name in z.namelist():
            if name.startswith('src/')or name in ('cfg/geos-editor-semantic-lex.cfg','tools/module_bindings.py','tools/bindings.py'):
                z.extract(name,out)
    report=json.loads((e/'editor-report.json').read_text());digest=report['resident_binding']['digest']
    (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
    def run(*args):
        p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
        with(out/'build.log').open('a')as f:f.write(p.stdout+p.stderr)
        assert not p.returncode,(args,p.stdout,p.stderr)
    objects=[]
    for name,source in (('worker','src/render/geos/semantic-lex.s'),('parser','src/supermark/lexer.s')):
        obj=out/(name+'.o');run('ca65','-g','-I',out,'-I',out/'src','-o',obj,out/source);objects.append(obj)
    run(sys.executable,out/'tools/module_bindings.py','--report',e/'editor-report.json','--output',out/'aliases.s',*objects)
    run('ca65','-g','-o',out/'aliases.o',out/'aliases.s')
    run('ld65','-C',out/'cfg/geos-editor-semantic-lex.cfg','-o',out/'worker.bin','-Ln',out/'worker.lbl','-m',out/'worker.map',*objects,out/'aliases.o')
    payload=(out/'worker.bin').read_bytes()
    assert payload==(e/'geoslex.seo').read_bytes()[36:],'trace symbols must match actual frozen C25 bytes'
    symbols={name:int(addr,16)for addr,name in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'worker.lbl').read_text())}
    active=json.loads((e/'freeze.json').read_text())['catalog'].index('geoslex')+1
    proof=dict(payload_sha256=hashlib.sha256(payload).hexdigest(),active_index=active,
               symbols={name:symbols[name]for name in ('entry','se_sl_init','se_sl_feed','se_sl_finish')},
               scope='Conditional native instruction traces; exact frozen-source rebuild, actual C25 active/busy only.')
    (e/'lexer-trace.json').write_text(json.dumps(proof,indent=2)+'\n');return proof


class Plan(caret.Plan):
    def raw(self,ident,commands):
        if ident.endswith('_timed_coherent'):
            proof=self.lex_trace
            condition=f'@cpu:${self.s["se_overlay_active"]+1:04x} == ${proof["active_index"]:02x} && @cpu:${self.s["se_overlay_busy"]+1:04x} == $01'
            commands=list(commands);at=commands.index('stopwatch reset')
            commands[at:at]=[f'trace exec ${pc:04x} if {condition}'for pc in proof['symbols'].values()]
        return super().raw(ident,commands)


def document(language):
    prefix='10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; '
    return timing.native.live.grid.native_text('Intro\r:::'+language+'\r'+prefix+'x'*980+'\r:::\rTail.')


def package(e):
    for language in ('basic','asm'):
        path=e/(language+'.seq');path.write_bytes(document(language))
        p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(path),language+'doc,s'],capture_output=True)
        (e/('package-'+language+'.log')).write_bytes(p.stdout+p.stderr);assert not p.returncode
        assert D81Image((e/'working.d81').read_bytes()).read((language+'doc').upper().encode(),kind=1).data==document(language)
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')


def scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0)
    n.lex_trace=lexer_trace(e)
    assert len(json.loads((e/'freeze.json').read_text())['catalog'])==59
    n.cost_profile=True;n.boot()
    for language in ('basic','asm'):
        data=document(language);n.open('open-'+language,(language+'doc').upper().encode())
        n.typed(language+'-baseline-markdown','syntax markdown')
        if language=='basic':n.typed(language+'-hires','mode hires')
        # Establish a genuine non-lexical baseline before timing Full.
        n.raw(language+'-baseline-idle',['delete',f'break exec ${n.idle_pc:04x} if {n.condition(0)}','x','delete'])
        n.memory(language+'-caps-before','se_render_caps',1)
        n.send(language+'-full-prompt',b'\x88'+timing.native.live.grid.native_text('syntax full'),ui=2)
        n.snapshot(language+'-before',data,3,2)
        n.measure(language+'-first',data,3,key=13,category='automatic-first-construction')
        n.measurements[-1].update(language=language,caps=3,phase='first')
        n.measure(language+'-warm',data,3,full=True,category='retained-lexical-full-repaint')
        n.measurements[-1].update(language=language,caps=3,phase='warm')
        for preset,caps in (('plain',0),('markdown',1)):
            n.typed(language+'-'+preset+'-apply','syntax '+preset)
            n.measure(language+'-'+preset,data,3,full=True,category='lexer-bypass')
            n.measurements[-1].update(language=language,caps=caps,phase=preset)
    return n


def arena(n,ram,reu):
    s=n.s;token=ram[s['se_bc_arena']:s['se_bc_arena']+5];oid=token[0]
    assert token!=bytes(5) and oid<8 and ram[s['object_owner']+oid]==0x53
    assert token[1:3]==bytes((ram[s['object_gen_lo']+oid],ram[s['object_gen_hi']+oid]))
    epoch=ram[s['se_object_epoch']:s['se_object_epoch']+2]
    assert token[3:]==epoch==ram[s['se_reu_epoch']:s['se_reu_epoch']+2] and epoch!=bytes(2)
    assert ram[s['object_banks']+oid]==1
    logical=ram[s['object_extents']+oid*16];bank=ram[s['se_reu_map']+logical]
    assert logical and bank and ram[s['se_reu_logical_owner']+logical]==ram[s['se_reu_physical_owner']+bank]==0x53
    lo=bank*65536;roots=[]
    for at in (0,128):
        r=reu[lo+at:lo+at+128]
        if r[:6]==b'BCA1\1\1'and int.from_bytes(r[119:121],'little')==binascii.crc_hqx(r[:5]+r[6:119]+r[121:],65535):roots.append((at,r))
    assert roots
    at,r=max(roots,key=lambda x:int.from_bytes(x[1][18:22],'little'))
    return dict(token=token.hex(),logical=logical,bank=bank),lo,at,r


def evaluate(n):
    original=timing.semantic.expected
    def expected(f,data,fonts):
        bits,attrs,rows=plain.expected(f,data,fonts,f.get('se_render_caps',1))
        return bits,attrs,rows,None
    timing.semantic.expected=expected
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original
    images=timing.native.live.grid.reu_images(n.out/'run');records=[]
    trace=json.loads((n.e/'lexer-trace.json').read_text())
    for language in ('basic','asm'):
        cap=n.out/'captures';before_id=language+'-before'
        before_ram=(cap/(before_id+'-ram.bin')).read_bytes();before=images[before_id]
        descriptor,lo,selected,oldroot=arena(n,before_ram,before)
        assert oldroot[31]==1 and not before_ram[n.s['se_bc_flags']]&128,'real nonlexical baseline required'
        canonical=None;retained=None
        for item in (x for x in result['measurements']if x['language']==language):
            ident=item['id'];ram=(cap/(ident+'-ram.bin')).read_bytes();reu=images[ident]
            f=Captured(n.s,ram,(cap/(ident+'-colors.bin')).read_bytes(),n.e)
            current,where,chosen,root=arena(n,ram,reu)
            assert current==descriptor and where==lo
            assert f.get('se_render_caps',1)==item['caps'] and not f.get('se_bc_flags',1)&8
            assert f.get('se_bc_flags',1)&128 and root[31]==5 and root[98]==1
            state=f.read(n.s['se_doc_roots'],512)+b''.join(f.read(n.s[name],width)for name,width in (
                ('se_doc_meta',15),('se_doc_length',3),('se_doc_generation',2),
                ('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_clip_token',5),('se_clip_length',3)))
            if canonical is None:canonical=state
            assert state==canonical and not f.get('se_hot_pending',1)
            groups=item['cost_profile']['groups'];workers={(g['slot'],g['id'])for g in groups}
            text=(n.out/('stopwatch-'+ident+'.log')).read_text(encoding='utf-8-sig')
            pcs=[int(x,16)for x in re.findall(r'(?m)^\.C:([0-9a-f]{4})\s',text,re.I)]
            lex_counts={name:pcs.count(pc)for name,pc in trace['symbols'].items()}
            c25_calls=sum(g['calls']for g in groups if(g['slot'],g['id'])==(1,25))
            assert lex_counts['entry']==c25_calls,(ident,'all actual C25 gateway entries traced',lex_counts,c25_calls)
            if item['phase']=='first':
                assert (1,47)in workers and(1,49)in workers,'genuine producer and COW linker required'
                assert chosen!=selected and reu[lo+selected:lo+selected+128]==before[lo+selected:lo+selected+128]
                pages=[];wanted=bytearray(before)
                for page in range(1,16):
                    at=lo+256+page*8
                    if before[at:at+8]!=reu[at:at+8]:
                        assert before[at:at+8]==bytes(8);pages.append(page)
                        wanted[at:at+8]=reu[at:at+8];a=lo+page*4096;wanted[a:a+4096]=reu[a:a+4096]
                assert len(pages)==2
                wanted[lo+chosen:lo+chosen+128]=reu[lo+chosen:lo+chosen+128]
                retained=reu[lo:lo+65536]
            else:
                assert (1,47)not in workers and(1,49)not in workers
                assert reu[lo:lo+65536]==retained,'retained syntax arena changed'
                wanted=bytearray(before);wanted[lo:lo+65536]=retained
            if item['phase']=='warm':
                assert (1,45)in workers,'warm code must consume through actual retained-role gateway'
                assert not any(lex_counts[k]for k in ('se_sl_init','se_sl_feed','se_sl_finish')),(ident,'warm C25 parsed instead of gateway',lex_counts)
            if item['caps']!=3:assert not workers&{(1,45),(1,47),(1,49),(1,25),(1,31),(0,31)}
            # Source FE is derived; all actual FE ownership graphs are checked.
            derived={b for raw in (before_ram,ram)for b in range(256)if raw[n.s['se_reu_physical_owner']+b]==0xfe}
            for bank in derived:
                assert ram[n.s['se_reu_physical_owner']+bank]in(0,0xfe)
                a=bank*65536;wanted[a:a+65536]=reu[a:a+65536]
            assert reu==wanted,(ident,'whole16MiB outside actualCOW+FE')
            records.append(dict(id=ident,cycles=item['emulated_cycles'],loads=item['counter_deltas']['se_overlay_loads'],root_flags=root[31],arena_sha256=hashlib.sha256(retained).hexdigest(),C25_trace=lex_counts))
    caret.free_ports()
    summary=dict(status='PASS',scope=__doc__,identity=result['identity'],frames=records,
                 native_pixels=result['native_pixels'],visual_review='pending',ports_released=True)
    (n.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True);return summary


def execute(source=None,existing=None,verify=False):
    caret.free_ports()
    if existing:e=existing.resolve()
    else:
        e=timing.freeze(source.resolve(),'pal');target=e.with_name(e.name.replace('display-timing-pal','lexical-cache-native'));e.rename(target);e=target;package(e)
    if verify:
        n=caret.presentation.scenario_loaded(e);return evaluate(n)
    n=scenario(e);p=n.plan();assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('tests','tools'):
            for path in(ROOT/folder).glob('*.py'):z.write(path,path.relative_to(ROOT))
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('NATIVE_LEXICAL',e,len(n.measurements),'frames',flush=True)
    capacity.run_owned_plan(p,n.out,timeout=1200);return evaluate(n)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--existing',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
    execute(a.source,a.existing,a.verify)
