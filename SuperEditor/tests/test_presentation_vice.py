"""Owned PAL preset source/gallery/timing gate; actual typed commands and ROM I/O.

Uses an already frozen canonical product. No app image substitution, source/map
seeding, shared build, or physical keyboard latency claim. Timing uses the
existing explicit public-entry PC/SP seam; setup commands are IRQ bytes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,subprocess,zipfile
import test_display_timing_vice as timing
import test_geos_preview_vice as preview
import test_reu_capacity_vice as capacity
from test_fold_retention_vice import Captured
from d81_image import D81Image
import vice_plan
ROOT=timing.ROOT


class Plan(timing.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1
        assert not p['global_defaults'].get('kill_stale',False) and not p['steps'][0]['params']['kill_stale']
        return p
    def condition(self,ui):
        pairs=[('se_e_ui',ui),('se_e_job',0),('se_e_redraw',0),('se_e_draw_busy',0),('se_doc_read_locks',0),('se_f_owner',0),('se_input_nmi_pending',0),('se_overlay_busy',0)]
        # An open source40 command prompt deliberately parks optional styling.
        # Applying the preset must cancel it; do not wait for impossible idle
        # background work while UI2 owns the input prompt.
        if ui==0:pairs.append(('se_st_request',0))
        c=' && '.join(f'(@cpu:${self.s[n]:04x} == ${v:02x})' for n,v in pairs)
        return c+f' && (@cpu:${self.s["se_overlay_busy"]+1:04x} == $00) && (@cpu:${self.s["se_input_head"]:04x} == @cpu:${self.s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00)'


def package(e):
    data=timing.native.live.grid.fixture();(e/'diverse.bin').write_bytes(data)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'diverse.bin'),'diverse,s'],capture_output=True,text=True)
    (e/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(b'DIVERSE',kind=1).data==data
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')


def scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True
    data=timing.native.live.grid.fixture();n.boot();n.memory('startup_full','se_render_caps',3)
    n.open('open_diverse',b'DIVERSE')
    n.send('plain_command_prompt',b'\x88'+timing.native.live.grid.native_text('syntax plain'),ui=2)
    n.measure('plain40',data,0,key=13,category='preset-apply-through-first-draw')
    n.memory('typed_plain_applied','se_render_caps',0)
    for mode,width in [(1,60),(2,80)]:
        n.mode_to(mode);n.memory('plain_caps_'+str(width),'se_render_caps',0)
        n.measure('plain'+str(width),data,mode,full=True,category='forced-literal-repaint')
    n.typed('plain_geos_mode','mode hires');n.memory('plain_geos_caps','se_render_caps',0)
    n.measure('plain-geos',data,3,full=True,category='forced-literal-repaint')
    n.typed('open_preset_settings','settings',ui=1)
    n.measure('plain-settings',data,3,ui=1,full=True,category='settings-on-literal-body')
    n.send('H_to_markdown',timing.native.live.grid.native_text('h'),ui=1);n.memory('H_markdown_caps','se_render_caps',1)
    n.send('close_settings_markdown',b'\r')
    n.measure('markdown-geos',data,3,full=True,category='structure-no-lexer-repaint')
    n.typed('full_command','syntax full');n.memory('typed_full_applied','se_render_caps',3)
    n.measure('full-geos',data,3,full=True,category='full-semantic-repaint')
    for name,caps,preset in [('full',3,None),('markdown',1,'syntax markdown'),('plain',0,'syntax plain')]:
        if preset:n.typed('preview_preset_'+name,preset)
        n.send('preview_prompt_'+name,b'\x88'+timing.native.live.grid.native_text('preview'),ui=2)
        n.measure('preview-'+name,data,3,key=13,ui=4,category='explicit-preview-entry')
        n.send('preview_exit_'+name,b'\r')
    n.measure('plain-geos-return',data,3,full=True,category='literal-after-explicit-preview')
    for item,caps in zip(n.measurements,[0,0,0,0,0,1,3,3,1,0,0]):item['caps']=caps
    return n


def expected_geos(f,data,fonts):
    caps=f.get('se_render_caps',1)
    if caps==0:
        bits,attrs,rows=timing.native.live.geos.body_model(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor')if f.get('se_sel_mark',1)else None)
        model=None
    elif caps==1:
        model=timing.semantic.classify(data);roles=bytearray(model.roles)
        for e in model.events:
            if e['kind']==5:
                stop=e['end']+int(e['end']<len(data)and data[e['end']]==13)
                roles[e['start']:stop]=bytes([4])*(stop-e['start'])
        bits,attrs,rows=timing.semantic.raster(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),styles=model.styles,roles=roles,reverse=model.reverse,code=model.code)
        attrs=bytearray(attrs)
        for row in rows:
            if row.height==8:
                for col,at in enumerate(range(row.start,row.end)):attrs[(row.top//8)*40+col]=(timing.semantic.PALETTE[roles[at]]<<4)|6
        attrs=bytes(attrs)
    else:
        bits,attrs,rows,model=timing.semantic.body(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'))
    matrix,colors,popup=timing.native.live.geos.grid.logical_ui(f,data)
    bits,attrs=timing.native.live.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
    if f.get('se_e_ui',1)==1 and f.get('se_e_menu',1)==8:
        ui=preview.settings_ui(f,data,f.read(f.s['se_editor_settings'],64),f.get('se_e_item',1),True)
        ui.put(20,3,'H source mode:');ui.put(20,17,{0:'Plain',1:'Markdown',3:'Full'}[caps])
        bits,attrs=bytearray(bits),bytearray(attrs);timing.native.live.grid.paint_native(bits,attrs,ui,fonts['native8.bin']);bits,attrs=bytes(bits),bytes(attrs)
    return bits,attrs,rows,model


def evaluate(n):
    original=timing.semantic.expected;original_catalog=timing.FontCatalog;original_render=timing.render;timing.semantic.expected=expected_geos
    preview_caps=iter(item['caps']for item in n.measurements if item['ui']==4)
    def preset_preview(*args,**kwargs):
        return original_render(*args,**kwargs,code_coloring=bool(next(preview_caps)&2))
    timing.render=preset_preview
    timing.FontCatalog=lambda path,native:preview.pack_catalog((n.e/'font-pack.bin').read_bytes(),native)
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original;timing.FontCatalog=original_catalog;timing.render=original_render
    s=n.s;images=timing.native.live.grid.reu_images(n.out/'run');stable=None;outside=None;intervals=0
    derived=set()
    for item in n.measurements:
        ram=(n.out/'captures'/(item['id']+'-ram.bin')).read_bytes()
        derived.update(bank for bank in range(256)if ram[s['se_reu_physical_owner']+bank]==0xFE)
    for item in n.measurements:
        ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);reu=images[ident]
        assert f.get('se_render_caps',1)==item['caps']
        assert not any(f.get(k,1)for k in ('se_hot_pending','se_h_dirty','se_sel_mark'))
        assert f.get('se_hot_caret')==0 and f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'DIVERSE'
        assert f.read(s['se_editor_settings'],64)==(n.e/'editor-defaults.bin').read_bytes()
        canonical=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w)for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        if stable is None:stable=canonical
        assert stable==canonical,(ident,'source/history/clipboard preservation')
        masked=bytearray(reu)
        for bank in derived:
            assert ram[s['se_reu_physical_owner']+bank]in (0,0xFE),(ident,'derivedbankwasforeign',bank)
            masked[bank*65536:(bank+1)*65536]=bytes(65536)
        sha=hashlib.sha256(masked).hexdigest()
        if outside is None:outside=sha
        else:assert outside==sha,(ident,'whole16MiB outside typedderivedFE');intervals+=1
        groups=item.get('cost_profile') # timing.evaluate creates its own result items
        measured=next(x for x in result['measurements']if x['id']==ident)
        calls={(x['slot'],x['id'])for x in measured['cost_profile']['groups']}
        if item['caps']==0 and item['ui']!=4:
            assert not calls&{(1,14),(1,15),(1,19),(1,24),(1,25),(1,26),(1,31),(0,31)},(ident,'Plain scheduled semantic worker',calls)
            assert f.get('se_st_request',1)==f.get('se_st_valid',1)==0
        if item['caps']==1:assert not calls&{(1,15),(1,25),(1,31),(0,31)},(ident,'Markdown scheduled lexical worker')
    assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
    result.update(preset_source_checks='passed',whole16MiB_derived_only_intervals=intervals,presentation_scope='ActualPALsource/settings/explicit-previewcaptures, allVICpixels independently modeled. Typedpreset setup throughIRQ input; measure finalPlainRETURN through public-input seam. No physicalkeyboard claim. Overlayentry traces prove no semantic workerrequests in measuredPlain intervals; pureparser-zero acrossidle is CPUgate scope.')
    (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args();e=a.freeze.resolve()
    if a.verify:
        n=scenario_loaded(e);evaluate(n);return
    package(e);n=scenario(e);plan=n.plan();assert len({x['id']for x in plan['steps']})==len(plan['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('tests','tools'):
            for q in (ROOT/folder).glob('*.py'):z.write(q,q.relative_to(ROOT))
    print('PREPARED',e,'binary8100/text8200..8239','steps',len(n.steps),'screens',len(n.measurements),flush=True)
    if not a.run:return
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert not build.returncode
    manifest=capacity.run_owned_plan(plan,n.out,timeout=900);(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result=evaluate(n);print('PASS',e,flush=True)
    for c in result['measurements']:print(json.dumps(dict(id=c['id'],first_publish_cycles=c['first_publish_cycles'],settled_cycles=c['emulated_cycles'],loads=c['counter_deltas']['se_overlay_loads'])),flush=True)


def scenario_loaded(e):
    # Construct without adding/overwriting a finished plan or invoking native.
    n=Plan.__new__(Plan);n.e=e;n.out=e/'timing';n.r=json.loads((e/'editor-report.json').read_text());n.s=n.r['symbols'];n.standard=1;n.model=0;n.measurement_warp=True;n.cost_profile=True;n.canary=bytes((i*73+29)&255 for i in range(1024))
    m=json.loads((n.out/'measurements.json').read_text());n.measurements=m
    metadata=n.out/'plan-metadata.json'
    if not metadata.exists():
        # Retrospective host-only derivation for the first completed run. It
        # reads the identical frozen PRG/aliases, never emulator state.
        context=e/'verification-context';context.mkdir(exist_ok=True)
        for name in ('editor.prg','freeze.json'):shutil.copy2(e/name,context/name)
        template=Plan(context,n.r,1,0)
        metadata.write_text(json.dumps(dict(cold_end=template.cold_end,service_return=template.service_return,publish_pc=template.publish_pc,cost_points=template.cost_points,derivation='Host-only after run from frozen PRG; no native state changes'),indent=2)+'\n')
    meta=json.loads(metadata.read_text());n.cold_end=meta['cold_end'];n.service_return=meta['service_return'];n.publish_pc=meta['publish_pc'];n.cost_points=meta['cost_points'];return n


if __name__=='__main__':main()
