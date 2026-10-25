"""Bounded native wrap/pan policy proof on an explicitly frozen final preset build.

All view transitions use real typed commands. No host cache invalidation or
source/layout replacement; the existing public-entry stopwatch seam only times
ordinary redraw after each transition. Own8100/text8200, GUID run/PID/disk.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_presentation_vice as presets
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan,cpu_editor
ROOT=presets.ROOT;timing=presets.timing
DATA=timing.native.live.grid.native_text('W'*100+'\rShort.\rEnd.')
PREVIOUS=ROOT/'agentsworking/evidence/M8/20261025T222119881361Z-presentation-final-native'
EXPECTED='19fe3c991c196b4321c904c71c1e99482a1c049a6efc29fbae13757323f0ede4'


def freeze():
    e=ROOT/'agentsworking/evidence/M8'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-presentation-wrap-native');e.mkdir(parents=True)
    old=json.loads((PREVIOUS/'freeze.json').read_text());b=ROOT/'build'
    for name in ('editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81'):shutil.copy2(b/name,e/name)
    assert hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest()==EXPECTED
    assert hashlib.sha256((e/'editor.prg').read_bytes()).hexdigest()==old['prg_sha256']
    disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
    changed=[]
    for name in old['catalog']:
        image=(b/'overlays'/(name+'.seo')).read_bytes();assert disk.read(name.upper().encode(),kind=1).data==image
        assert image[20:36]==image[36:52]==bytes.fromhex(old['resident_binding']);(e/(name+'.seo')).write_bytes(image)
        if image!=(PREVIOUS/(name+'.seo')).read_bytes():
            changed.append(name);assert len(image)==len((PREVIOUS/(name+'.seo')).read_bytes())+12
    assert set(changed)=={'navigate','geosnav'},changed
    for name in ('bsw9.bin','bsw9-widths.bin','bsw9-original.bin','native8.bin','chargen.bin','font-pack.bin','editor-defaults.bin','editor-font-catalog.bin','presentation-defaults.inc'):shutil.copy2(PREVIOUS/name,e/name)
    with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('src','cfg','config'):
            for p in (ROOT/folder).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(ROOT))
        for p in (ROOT/'tools').glob('*.py'):z.write(p,p.relative_to(ROOT))
        z.write(ROOT/'Makefile','Makefile')
    identity=dict(old,disk_sha256=EXPECTED,asset_sha256={name:hashlib.sha256((e/(name+'.seo')).read_bytes()).hexdigest()for name in old['catalog']},changed_assets=changed,previous_native=str(PREVIOUS),product_sources_sha256=hashlib.sha256((e/'product-sources.zip').read_bytes()).hexdigest())
    (e/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');shutil.copy2(e/'supereditor.d81',e/'working.d81');(e/'wrappan.bin').write_bytes(DATA)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'wrappan.bin'),'wrappan,s'],capture_output=True,text=True);(e/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(b'WRAPPAN',kind=1).data==DATA;shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    print('FROZEN',e,'changed',changed,flush=True);return e


def scenario(e):
    n=presets.Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True
    n.boot();n.open('open_wrappan',b'WRAPPAN');n.typed('plain','syntax plain');n.typed('GEOS','mode hires')
    for ident,command,nowrap,caret in [('long-wrapped',None,0,0),('long-nowrap','wrap off',1,0),('long-rewrapped','wrap on',0,0),('short-pan-clamped','pan right',1,101)]:
        if ident=='short-pan-clamped':n.typed('short_logical_line','goto 2')
        if command:n.typed('transition_'+ident,command)
        n.memory(ident+'_plain','se_render_caps',0);n.memory(ident+'_policy','se_l_mode',nowrap);n.memory(ident+'_pan','se_l_pan',0,3);n.memory(ident+'_caret','se_hot_caret',caret,3)
        n.measure(ident,DATA,3,category='ordinary-redraw-after-typed-transition')
        n.measurements[-1].update(nowrap=nowrap,pan=0,caret=caret)
    return n


def expected(f,data,fonts):
    bits,attrs,rows=timing.native.live.geos.body_model(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
    matrix,colors,popup=timing.native.live.geos.grid.logical_ui(f,data)
    bits,attrs=timing.native.live.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
    return bits,attrs,rows,None


def evaluate(n):
    original=timing.semantic.expected;catalog=timing.FontCatalog;timing.semantic.expected=expected;timing.FontCatalog=lambda path,native:presets.preview.pack_catalog((n.e/'font-pack.bin').read_bytes(),native)
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original;timing.FontCatalog=catalog
    images=timing.native.live.grid.reu_images(n.out/'run');s=n.s;stable=None;outside=None;intervals=0;derived=set();prefixes=[]
    fonts={name:(n.e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)}
    for item in n.measurements:
        raw=(n.out/'captures'/(item['id']+'-ram.bin')).read_bytes();derived.update(bank for bank in range(256)if raw[s['se_reu_physical_owner']+bank]==0xFE)
    for item in n.measurements:
        ident=item['id'];raw=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,raw,colors,n.e);reu=images[ident]
        assert f.get('se_render_caps',1)==0 and f.get('se_l_mode',1)==item['nowrap'] and f.get('se_l_pan')==item['pan'] and f.get('se_hot_caret')==item['caret']
        assert f.get('se_st_request',1)==f.get('se_st_valid',1)==f.get('se_hot_pending',1)==f.get('se_h_dirty',1)==0
        assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'WRAPPAN'
        assert f.read(s['se_editor_settings'],64)==(n.e/'editor-defaults.bin').read_bytes()
        canonical=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w)for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        if stable is None:stable=canonical
        assert stable==canonical,(ident,'canonical/history/clipboard changed')
        masked=bytearray(reu)
        for bank in derived:assert raw[s['se_reu_physical_owner']+bank]in (0,0xFE);masked[bank*65536:(bank+1)*65536]=bytes(65536)
        digest=hashlib.sha256(masked).hexdigest()
        if outside is None:outside=digest
        else:assert outside==digest,(ident,'whole16MiB outside typedFE');intervals+=1
        _,_,rows,_=expected(f,DATA,fonts)
        handle=f.get('se_gc_handle',1);bank=raw[s['se_reu_map']+handle];assert raw[s['se_reu_logical_owner']+handle]==raw[s['se_reu_physical_owner']+bank]==0xFE
        cache=reu[bank*65536:(bank+1)*65536];assert cache[0]==1 and cache[1]==len(rows)
        actual=[]
        for i,row in enumerate(rows):
            p=cache[0x200+i*0x800:0x220+i*0x800];anchors=tuple(int.from_bytes(p[x:x+3],'little')for x in (0,3,6));assert anchors==(row.start,row.end,row.next),(ident,'independentrowanchors',anchors,row)
            actual.append(anchors)
        prefixes.append(actual)
        measure=next(x for x in result['measurements']if x['id']==ident);calls={(x['slot'],x['id'])for x in measure['cost_profile']['groups']}
        assert not calls&{(1,14),(1,15),(1,19),(1,24),(1,25),(1,26),(1,31),(0,31)},(ident,'Plain semantic request')
    assert prefixes[0]==prefixes[2] and len(prefixes[0])>len(prefixes[1])
    assert (n.out/'native-long-wrapped.png').read_bytes()==(n.out/'native-long-rewrapped.png').read_bytes()
    assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
    result.update(wrap_policy='PASS: wrapped→nowrap→wrapped restores exactnativeframe/independentanchors; shortcurrentlinePANright clamps0andautoenablesnowrap.',cache_invalidation='Productonly; verifierdoesNOTwritevalidflags/pan/mode/maps.',whole16MiB_derived_only_intervals=intervals,independent_row_anchors=prefixes,ancestry='Earlier96e11frames retained; onlynavigate/geosnav assets +12B each incurrent19feD81, renderers/resident unchanged.')
    (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--freeze',type=Path);a=p.parse_args();e=a.freeze.resolve()if a.freeze else freeze();n=scenario(e);plan=n.plan()
    (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('tests','tools'):
            for p in (ROOT/folder).glob('*.py'):z.write(p,p.relative_to(ROOT))
    print('PREPARED',e,'8100/text8200..8239','steps',len(n.steps),'screens4',flush=True)
    if not a.run:return
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert not p.returncode
    manifest=presets.capacity.run_owned_plan(plan,n.out,timeout=900);(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');result=evaluate(n);print('PASS',e,flush=True)
    for item in result['measurements']:print(json.dumps(dict(id=item['id'],first=item['first_publish_cycles'],settled=item['emulated_cycles'],loads=item['counter_deltas']['se_overlay_loads'])),flush=True)


if __name__=='__main__':main()
