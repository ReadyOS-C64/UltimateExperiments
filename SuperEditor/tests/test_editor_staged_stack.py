"""Close the foreground stack graph over authenticated R31/C31 and R30/C32 code.

No shared build or verifier mutation. Each renderer receives only its own
authenticated5000 stage; other modules still reject that unmapped address range.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, binascii, hashlib, importlib.util, inspect, json, re, shutil, sys, zipfile
import test_editor_kernal_stack as original

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'build/geos-incremental-editor/20261025T104900415766Z/fixture'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stage_proof(out, base):
    frozen = json.loads((base / 'freeze.json').read_text())
    report = json.loads((base / 'build/editor-report.json').read_text())
    expected_tail = {46:['code','clex'],47:['code','clex','type'],48:['code','clex','type','grid'],49:['code','clex','type','grid','hotcold']}
    assert len(frozen['names']) in expected_tail
    assert frozen['names'][-len(expected_tail[len(frozen['names'])]):] == expected_tail[len(frozen['names'])]
    assert sha((base / 'build/editor.prg').read_bytes()) == frozen['prg_sha256'] == report['sha256']
    images = {n: (base / 'build/overlays' / (n + '.seo')).read_bytes() for n in ('code', 'clex')}
    digest = bytes.fromhex(report['resident_binding']['digest'])
    for name, image in images.items():
        assert sha(image) == frozen['assets'][name]
        assert image[:4] == b'SEO2' and image[5] == (name == 'clex') and image[6] == 31
        assert image[20:36] == image[36:52] == digest
        assert int.from_bytes(image[8:10], 'little') == len(image) - 36
        assert binascii.crc_hqx(image[36:], 0xffff) == int.from_bytes(image[12:14], 'little')
    payload = images['clex'][36:]
    # A C31 call remains the harmless ordinary B010 entry. Only its separately
    # staged raw CODE can be entered at5000 after the R31 admission/CRC guard.
    assert payload[16:20] == bytes.fromhex('a9001860')
    project = out / 'private-project'
    project.mkdir()
    with zipfile.ZipFile(base / 'product-sources.zip') as archive:
        for name in archive.namelist():
            if name.startswith('src/') and not name.endswith('/'):
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
    shutil.copytree(ROOT / 'tools', project / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
    builder = ROOT / 'src/render/geos/code-typing/build-stage.py'
    spec = importlib.util.spec_from_file_location('frozen_stage_builder', builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = project  # all production assembler inputs come from frozen ZIP
    stage = out / 'stage'
    module.build(stage, base)
    assert (stage / 'stage.seo').read_bytes() == images['clex'], 'private stage differs from frozen sealed C31'
    assert (stage / 'stage.bin').read_bytes() == payload
    labels = {}
    for line in (stage / 'stage.lbl').read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == 'al':
            labels[parts[2].lstrip('.')] = int(parts[1], 16)
    assert labels['__CODE_LOAD__'] == 0xb020
    assert labels['__CODE_RUN__'] == labels['se_gct_stage_lex'] == 0x5000
    assert labels['se_gct_stage_paint'] == 0x5003
    raw = payload[32:]
    constants=(stage/'stage-constants.inc').read_text()
    assert 'GCT_STAGE_ID=31' in constants and 'GCT_STAGE_VALID=$41' in constants
    assert 0 < len(raw) < 4096 and raw[0] == raw[3] == 0x4c
    cfg = (project / 'src/render/geos/code-typing/stage.cfg').read_text()
    # Parse the actual linker placement, rather than deriving a run address
    # from entry labels or treating the payload as if linked at B020.
    memory_text = re.search(r'MEMORY\s*\{(.*?)\}',cfg,re.S).group(1)
    segment_text = re.search(r'SEGMENTS\s*\{(.*?)\}',cfg,re.S).group(1)
    memory = {}
    for name, fields in re.findall(r'(\w+)\s*:(.*?);',memory_text,re.S):
        memory[name] = {key:int(value,16) for key,value in re.findall(r'(start|size)\s*=\s*\$([0-9a-fA-F]+)',fields)}
    assert memory == dict(IMAGE=dict(start=0xb000,size=0x1000),STAGE=dict(start=0x5000,size=0x1000),PHASE=dict(start=0x8d00,size=0x3c))
    segments = {name:dict(re.findall(r'(\w+)\s*=\s*(\w+)',fields)) for name,fields in re.findall(r'(\w+)\s*:(.*?);',segment_text,re.S)}
    assert segments['C31_HEADER']['load']=='IMAGE'
    for name in ('CODE','SM_LEXER','RODATA'):
        assert segments[name]['load']=='IMAGE' and segments[name]['run']=='STAGE'
    assert segments['SM_STATE']['load']=='PHASE' and segments['SM_STATE']['type']=='bss'
    proof = dict(status='byte-identical',fixture=str(base), assets=len(frozen['names']),
        binding=digest.hex(), resident_sha256=frozen['prg_sha256'],
        sealed_image_sha256=sha(images['clex']), raw_sha256=sha(raw),
        payload_bytes=len(payload), header_bytes=32, raw_bytes=len(raw),
        payload_crc16=binascii.crc_hqx(payload,0xffff), raw_crc16=binascii.crc_hqx(raw,0xffff),
        raw_run=0x5000, namespace_valid=0x41, stage_id=31, entries={k:labels[k] for k in ('se_gct_stage_lex','se_gct_stage_paint','se_gct_lex','se_gct_paint')},
        stage_cfg_sha256=sha(cfg.encode()), parsed_memory=memory, parsed_segments=segments, builder_sha256=sha(builder.read_bytes()),
        source_zip_sha256=sha((base/'product-sources.zip').read_bytes()))
    (out / 'stage-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return raw, labels, proof


def style_stage_proof(out,base):
    """Authenticate and reassemble both halves of the C32/R30 helper ABI."""
    frozen=json.loads((base/'freeze.json').read_text())
    if 'type' not in frozen['names']:return None
    report=json.loads((base/'build/editor-report.json').read_text());digest=bytes.fromhex(report['resident_binding']['digest'])
    images={name:(base/'build/overlays'/(name+'.seo')).read_bytes()for name in ('gtype','type')}
    for name,image in images.items():
        assert sha(image)==frozen['assets'][name]
        assert image[:4]==b'SEO2'and image[5:7]==bytes((0,30)if name=='gtype'else(1,32))
        assert image[20:36]==image[36:52]==digest
        assert int.from_bytes(image[8:10],'little')==len(image)-36
        assert binascii.crc_hqx(image[36:],0xffff)==int.from_bytes(image[12:14],'little')
    project=out/'private-project';builder=ROOT/'src/render/geos/style-typing/build.py'
    # The election helper embeds its immutable width table. Reassemble with
    # the fixture's authenticated font, never the current working tree font.
    font_inputs={}
    if (project/'src/render/geos/style-typing/two-color.s').is_file():
        name='bsw9-widths.bin';font=base/'fonts'/name
        assert sha(font.read_bytes())==frozen['fonts'][name]
        target=project/'assets/fonts/generated'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(font,target);font_inputs[name]=sha(font.read_bytes())
    spec=importlib.util.spec_from_file_location('frozen_style_builder',builder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=project;module.D=project/'src/render/geos/style-typing'
    target=out/'style-stage';rebuilt,budget=module.build(target,base)
    assert rebuilt['stage']==images['type'] and rebuilt['worker']==images['gtype'],'C32/R30 private reassembly differs'
    def labels(path):
        result={}
        for line in path.read_text().splitlines():
            parts=line.split()
            if len(parts)==3 and parts[0]=='al':result[parts[2].lstrip('.')]=int(parts[1],16)
        return result
    sl=labels(target/'stage.lbl');rl=labels(target/'worker.lbl');payload=images['type'][36:];raw=payload[32:];worker=images['gtype'][36:]
    constants=(target/'stage-constants.inc').read_text()
    assert 'GCT_STAGE_ID=32' in constants and 'GCT_STAGE_VALID=$42' in constants
    assert payload[16:20]==bytes.fromhex('a9001860')and sl['__CODE_LOAD__']==0xb020 and sl['__CODE_RUN__']==0x5000
    assert raw[0]==0x4c and int.from_bytes(raw[1:3],'little')==sl['se_gst_transaction']
    assert len(raw)<=0xfe0 and not budget['new_BSS']and not budget['new_ZP']
    helper_names=['se_gtt_admit','se_gtt_current','se_gp_cache_slot','se_gp_cache_read','se_gp_cache_write','se_gcc_status']
    if (project/'src/render/geos/style-typing/two-color.s').is_file():
        helper_names.append('se_tcb_two_check')
    assert set(budget['vectors']) == set(helper_names)
    vectors={}
    for index,name in enumerate(helper_names):
        address=0xa020+index*3;offset=address-0xa000
        assert budget['vectors'][name]==sl[name]==address
        assert worker[offset]==0x4c
        destination=int.from_bytes(worker[offset+1:offset+3],'little')
        assert destination==rl[name] and 0xa000<=destination<0xa000+len(worker)
        vectors[name]=dict(vector=address,destination=destination)
    cfg=(project/'src/render/geos/style-typing/stage.cfg').read_text()
    memory={name:{k:int(v,16)for k,v in re.findall(r'(start|size)\s*=\s*\$([0-9a-fA-F]+)',fields)}for name,fields in re.findall(r'(\w+)\s*:(.*?);',re.search(r'MEMORY\s*\{(.*?)\}',cfg,re.S).group(1),re.S)}
    segments={name:dict(re.findall(r'(\w+)\s*=\s*(\w+)',fields))for name,fields in re.findall(r'(\w+)\s*:(.*?);',re.search(r'SEGMENTS\s*\{(.*?)\}',cfg,re.S).group(1),re.S)}
    assert memory==dict(IMAGE=dict(start=0xb000,size=0x1000),STAGE=dict(start=0x5000,size=0xfe0))
    assert segments['STYLE_HEADER']['load']=='IMAGE'
    for name in ('CODE','RODATA'):assert segments[name]['load']=='IMAGE'and segments[name]['run']=='STAGE'
    proof=dict(status='byte-identical',namespace_valid=0x42,renderer='gtype',module_ids=dict(renderer=30,stage=32),payload_bytes=len(payload),raw_bytes=len(raw),raw_crc16=binascii.crc_hqx(raw,0xffff),payload_crc16=binascii.crc_hqx(payload,0xffff),raw_sha256=sha(raw),stage_sha256=sha(images['type']),renderer_sha256=sha(images['gtype']),renderer_bytes=len(worker),entry=0x5000,transaction_entry=sl['se_gst_transaction'],helper_vectors=vectors,parsed_memory=memory,parsed_segments=segments,stage_cfg_sha256=sha(cfg.encode()),builder_sha256=sha(builder.read_bytes()))
    proof['font_inputs']=font_inputs
    (out/'style-stage-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return raw,sl,proof


def raster_phase_proof(out,base):
    """Bound only R21's byte-checked shift dispatch by its longest suffix chain."""
    with zipfile.ZipFile(base/'product-sources.zip')as z:
        source=z.read('src/render/geos/literal-byte/glyph.s')
    if b'phase_lo:'not in source:return None
    import test_geos_strip_raster_candidate as row
    _,symbols,labels,raw,image,_=row.build(out/'raster-phase-reassembly',base,'control')
    assert image==(base/'build/overlays/geosrow.seo').read_bytes()
    first,last=labels['phase7'],labels['phase0'];pointer=symbols['screen_ptr']
    at=lambda address,size:raw[address-0xa000:address-0xa000+size]
    chain=at(first,last-first)
    assert len(chain)==28 and chain==chain[:4]*7 and chain[0]==0x0e and chain[3]==0x2a
    assert last-first==28 and first>>8==last>>8
    targets=[labels['phase'+str(i)]for i in range(8)]
    assert targets==[last-4*i for i in range(8)]
    table=labels['phase_lo'];assert at(table,8)==bytes(v&255 for v in targets)
    # LDA lowtable,X; STA ptr; LDA#high; STA ptr+1; LDA inkHi; JMP(ptr).
    dispatch=at(first-15,15)
    expected=bytes((0xbd,table&255,table>>8,0x85,pointer,0xa9,first>>8,0x85,pointer+1,0xad))
    assert dispatch[:10]==expected and dispatch[-3:]==bytes((0x6c,pointer,0))
    assert at(last,3)[0]==0x8d and at(last,3)[1:]==dispatch[10:12]
    assert b'and #7\n    sta G+GG_PHASE'in source
    return dict(pointer=pointer,target=first,all_targets=targets,dispatch_pc=first-3,
                dispatch_hex=dispatch.hex(),chain_hex=chain.hex(),
                payload_sha256=hashlib.sha256(raw).hexdigest(),
                scope='R21 only; all eight targets share one stack-neutral fallthrough suffix. Longest chain covers every suffix instruction. No opaque call or global indirect exception.')


def run(out, base, rompath, idle_log=None):
    base = base.resolve()
    idle_log = idle_log.resolve() if idle_log else None
    raw, labels, proof = stage_proof(out, base)
    style=style_stage_proof(out,base)
    phase=raster_phase_proof(out,base)
    symbols=json.loads((base/'build/editor-report.json').read_text())['symbols']
    managed=symbols.get('se_overlay_managed_verification',0)
    assert managed in (0,1)
    proof['compiled_feature_flags']=[]
    if managed:
        # These flags are declared by the actual report/source build. They
        # affect IEC invalidation/cold placement, not the evaluator's graph.
        compilation=inspect.getsource(original.compiled_resident)
        old_compile="command('ca65','-g','-I',sources/'src','-o',obj,sources/'src'/source)"
        new_compile="command('ca65','-g','-D','EDITOR_MANAGED_CODE=1','-D','EDITOR_COLD_DISPATCH=1','-I',sources/'src','-o',obj,sources/'src'/source)"
        assert compilation.count(old_compile)==1
        compile_namespace=dict(original.__dict__)
        exec(compile(compilation.replace(old_compile,new_compile),str(Path(__file__))+':managed-compile','exec'),compile_namespace)
        original.compiled_resident=compile_namespace['compiled_resident']
        proof['compiled_feature_flags']=['EDITOR_MANAGED_CODE=1','EDITOR_COLD_DISPATCH=1']
        # Moved COLD hot initializer shares an actual four-byte warm return
        # tail immediately preceding se_hot_call. Decode those exact bytes;
        # do not invent an opaque helper for its previously unmapped RTS.
        prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little')
        tail=symbols['se_hot_call']-4
        assert prg[2+tail-load:2+tail-load+4]==bytes.fromhex('a9001860')
        caller_source=inspect.getsource(original.caller_proof)
        old_cold="[resident(cold['start'],cold['end']+1)],{s['se_overlay_read']:reader,s['se_overlay_call']:font+3})"
        new_cold="[resident(cold['start'],cold['end']+1),resident(s['se_hot_call']-4,s['se_hot_call'])],{s['se_overlay_read']:reader,s['se_overlay_call']:font+3})"
        assert caller_source.count(old_cold)==1
        caller_namespace=dict(original.__dict__)
        exec(compile(caller_source.replace(old_cold,new_cold),str(Path(__file__))+':cold-tail','exec'),caller_namespace)
        original.caller_proof=caller_namespace['caller_proof']
        proof['cold_shared_tail']=dict(start=tail,bytes='a9001860')
    # Retain the released evaluator, every branch/stack-content rule, nesting
    # summary, unknown-call rejection and existing IRQ proof unchanged. The
    # exact single extension supplies real authenticated bytes only for R31.
    source = inspect.getsource(original.foreground_proof)
    old = "[(0xa000,image[36:])],L,stops=[0x900]if name=='lifecopy'else())"
    new = "[(0xa000,image[36:])]+([(0x5000,STAGES[name])]if name in STAGES else[]),L,stops=[0x900]if name=='lifecopy'else())"
    assert source.count(old) == 1
    stages=dict(code=raw)
    if style:stages['gtype']=style[0]
    source=source.replace(old,new)
    vector_hook="  if name=='loader':a.vectors[s['ovl_ptr']]=0xb010"
    assert source.count(vector_hook)==1
    source=source.replace(vector_hook,"  if name=='R:geosrow' and PHASE:a.vectors[PHASE['pointer']]=PHASE['target']\n"+vector_hook)
    namespace = dict(original.__dict__, STAGES=stages,PHASE=phase)
    exec(compile(source, str(Path(__file__).resolve())+':foreground-extension', 'exec'), namespace)
    original.foreground_proof = namespace['foreground_proof']
    if idle_log:
        native = idle_log.parent.parent
        native_report = json.loads((native/'editor-report.json').read_text())
        assert native_report['sha256']==proof['resident_sha256']
        assert native_report['resident_binding']['digest']==proof['binding']
    result = original.run(out, rompath, base, foreground=True,idle_log=idle_log)
    fg = result['foreground']
    if phase:fg['raster_phase_dispatch']=phase
    stage_result = next(r for r in fg['results'] if r['name']=='R:code')
    reached = set(stage_result['instruction_addresses'])
    assert {0x5000,0x5003,labels['se_gct_lex'],labels['se_gct_paint']} <= reached
    assert not stage_result['faults']
    # No global address exception: the unchanged evaluator must still refuse
    # the exact same JSR5000 outside a correctly authenticated R31 context.
    rejections=[]
    for target in (0x5000,0x5003,0xa020,0xa02f,0xa032):
        code=bytes((0x20,target&255,target>>8,0x60))
        rejected=original.Analysis(rompath.read_bytes(),[(0x2000,code)]).analyze('unowned-%04x-must-reject'%target,0x2000)
        assert rejected['status']=='unresolved'and rejected['fault_count']>0
        rejections.append(rejected)
    rejection=rejections[0]
    assert all(set(r['opaque_non_IEC_calls']) <= {json.loads((base/'build/editor-report.json').read_text())['symbols']['se_overlay_call']} for r in fg['results'])
    fg['staged_image'] = proof
    fg['staged_instruction_addresses'] = sorted(a for a in reached if 0x5000<=a<0x5000+len(raw))
    r31 = (base/'build/overlays/code.seo').read_bytes()[36:]
    calls = []
    for pc in sorted(reached):
        if 0xa000 <= pc < 0xa000+len(r31)-2:
            instruction = r31[pc-0xa000:pc-0xa000+3]
            target = int.from_bytes(instruction[1:],'little')
            if instruction[0]==0x20 and target in (0x5000,0x5003):
                calls.append(dict(pc=pc,target=target))
    assert {call['target'] for call in calls}=={0x5000,0x5003}
    fg['staged_call_sites'] = calls
    if style:
        sr=next(r for r in fg['results']if r['name']=='R:gtype');addresses=set(sr['instruction_addresses'])
        assert {0x5000,style[1]['se_gst_transaction']}<=addresses and not sr['faults']
        assert {v['vector']for v in style[2]['helper_vectors'].values()}<=addresses
        fg['style_staged_image']=style[2]
        fg['style_staged_instruction_addresses']=sorted(pc for pc in addresses if 0x5000<=pc<0x5000+len(style[0]))
        r30=(base/'build/overlays/gtype.seo').read_bytes()[36:]
        fg['style_staged_call_sites']=[dict(pc=pc,target=0x5000)for pc in sorted(addresses)if 0xa000<=pc<0xa000+len(r30)-2 and r30[pc-0xa000:pc-0xa000+3]==bytes.fromhex('200050')]
        assert fg['style_staged_call_sites']
        helper_end=max(v['vector'] for v in style[2]['helper_vectors'].values())
        fg['scope']+=f" R30-only authenticated C32 raw stage at5000 and all {len(style[2]['helper_vectors'])} fixedA020..{helper_end:04X} helper JMPs fully decoded; both images byte-identically reassembled."
    fg['unowned_stage_rejected'] = rejection
    fg['unowned_stage_and_helper_refusals']=rejections
    fg['scope'] += ' R31-only authenticated C31 raw stage at5000/5003 is fully decoded after byte-identical private reassembly; no additional opaque edges.'
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('STAGED',json.dumps(dict(status=result['status'],R=fg['R'],C=fg['C'],foreground=fg['foreground_beyond_entry_idle'],relative_combined=fg['relative_combined'],staged_instructions=len(fg['staged_instruction_addresses']),raw_bytes=len(raw),style_staged_instructions=len(fg.get('style_staged_instruction_addresses',[])))),flush=True)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--rom',type=Path,default=original.ROM);p.add_argument('--idle-log',type=Path)
    args=p.parse_args();out=ROOT/'build/editor-staged-stack'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);run(out,args.fixture,args.rom,args.idle_log)
