"""Private current-C20 output certificate eliminates duplicate C21 inlinequery."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,zipfile,shutil,subprocess,sys,hashlib,binascii
import test_geos_semantic_editor as semantic
from overlays import wrap
ROOT=semantic.ROOT;D=ROOT/'src/render/geos/source-style-window-candidate';BASE=ROOT/'build/geos-paint-batch-native-input/20261025T190648774509Z/fixture'
def cmd(*a):
 p=subprocess.run(list(map(str,a)),cwd=ROOT,capture_output=True,text=True);assert not p.returncode,p.stdout+p.stderr

def build(out,base):
 out.mkdir(parents=True);src=out/'source';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 inc=out/'include/render/geos';inc.mkdir(parents=True)
 for p in D.iterdir():
  if p.suffix in('.s','.inc'):shutil.copy2(p,inc/p.name)
 shutil.copy2(ROOT/'src/render/geos/inline161-candidate/inline.inc',inc/'inline.inc')
 # Rebase the tiny C21 routing hook onto the exact frozen coordinator.
 page=D/'page.s'
 if base.resolve()!=BASE.resolve():
  original=(src/'src/render/geos/page.s').read_text()
  assert 'GI_BEGIN_WIDE' in original,'current baseline must include the released 161-byte ABI'
  hook='    lda #8\n    sta PS\n    lda #GI_ID\n    ldx #GI_BEGIN\n'
  replacement='    lda #8\n    sta PS\n    lda SC_VALID\n    cmp #2\n    bne :+\n    lda #GP_LAYOUT_ID\n    ldx #SC_CONSUME\n    jmp request\n:\n    lda #GI_ID\n    ldx #GI_BEGIN\n'
  assert original.count(hook)==1
  original=original.replace(hook,replacement).replace('.include \"render/geos/source-line.inc\"\n','.include \"render/geos/source-line.inc\"\n.include \"render/geos/source-certificate.inc\"\n',1)
  page=out/'page-rebased.s';page.write_text(original)
 seed=(base/'build/overlays/geossema.seo').read_bytes()[36:]
 (out/'consumer-witness.inc').write_text('GSC_SEED_SIZE='+str(len(seed))+'\nGSC_SEED_CRC='+str(binascii.crc_hqx(seed,65535))+'\n')
 r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols'];seal=r['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');records={}
 for name,id,files,cfg in [('geosline',20,[('source-line',D/'source-line.s'),('line',src/'src/render/geos/line.s'),('measure',src/'src/render/geos/measure.s'),('assets',src/'src/render/geos/assets.s')],'geos-editor-layout.cfg'),('geospage',21,[('page',page),('cache',src/'src/render/geos/cache.s')],'geos-editor-page.cfg')]:
  objs=[]
  for tag,path in files:
   o=out/(tag+'.o');cmd('ca65','-g',*(['-D','SE_EDITOR_GEOS_INLINE=1']if tag=='source-line'else[]),'-I',out,'-I',out/'include','-I',src/'src','-o',o,path);objs.append(o)
  cmd(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-bind.s'),*objs);cmd('ca65','-o',out/(name+'-bind.o'),out/(name+'-bind.s'));cmd('ld65','-C',src/'cfg'/cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs,out/(name+'-bind.o'))
  raw=(out/(name+'.bin')).read_bytes();assert len(raw)<=4096;image=wrap(raw,1,id,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/(name+'.seo')).write_bytes(image);records[name]={'payload':len(raw),'sha256':hashlib.sha256(image).hexdigest()}
 (out/'build.json').write_text(json.dumps(records,indent=2)+'\n');return records

def install(out,base):
 r=build(out/'link',base);f=out/'fixture';shutil.copytree(base,f);i=json.loads((f/'freeze.json').read_text())
 for n,v in r.items():shutil.copy2(out/'link'/(n+'.seo'),f/'build/overlays'/(n+'.seo'));i['assets'][n]=v['sha256']
 #Matching161publication C26 is required by the independent C21 controlsource.
 src=ROOT/'build/geos-inline161/20261025T185529043989Z-public/fixture/build/overlays/geosinln.seo' if base.resolve()==BASE.resolve() else base/'build/overlays/geosinln.seo';shutil.copy2(src,f/'build/overlays/geosinln.seo');i['assets']['geosinln']=hashlib.sha256(src.read_bytes()).hexdigest();i['private_CPU_substitutions']=['geosline','geospage','geosinln'];i['native_disk_packaged']=False;(f/'freeze.json').write_text(json.dumps(i,indent=2)+'\n');return f
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fit','inline','profile','fold','incremental','capacity'],default='fit');p.add_argument('--control',action='store_true');p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();base_input=a.base.resolve();out=ROOT/'build/geos-style-certificate'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite+('-control'if a.control else''));out.mkdir(parents=True);print('RUN',out,flush=True)
 if a.suite=='fit':print(build(out/'link',base_input),flush=True)
 else:
  if a.control:
   base=out/'fixture';shutil.copytree(base_input,base);i=json.loads((base/'freeze.json').read_text())
   for n in(('geospage','geosinln')if base_input==BASE.resolve()else()):
    p=ROOT/'build/geos-inline161/20261025T185529043989Z-public/fixture/build/overlays'/(n+'.seo');shutil.copy2(p,base/'build/overlays'/(n+'.seo'));i['assets'][n]=hashlib.sha256(p.read_bytes()).hexdigest()
   (base/'freeze.json').write_text(json.dumps(i,indent=2)+'\n')
  else:base=install(out,base_input)
  gate=out/'gate';gate.mkdir()
  if a.suite=='inline':semantic.run(gate,base,inline_case=True)
  elif a.suite=='fold':
   import test_geos_fold_editor as gate_module;gate_module.run(gate,base)
  elif a.suite=='incremental':
   import test_geos_incremental_editor as gate_module;gate_module.run(gate,base)
  elif a.suite=='capacity':
   import test_geos_inline161_candidate as gate_module,inspect
   source=inspect.getsource(gate_module.public).replace("assert not any(f.get(n,1)for n in ('se_f_owner','se_fs_owned','se_doc_read_locks'))","assert not any(f.get(n,1)for n in ('se_f_owner','se_fs_owned','se_doc_read_locks')),(tag,{n:f.get(n,1)for n in ('se_f_owner','se_fs_owned','se_doc_read_locks','se_e_error','se_e_job')},f.read(0x912C,8).hex())")
   ns=dict(gate_module.__dict__);exec(source,ns);ns['public'](gate,base)
  else:
   import test_geos_inline_query_profile as profile;profile.run(gate,base)
