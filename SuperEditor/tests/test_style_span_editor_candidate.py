"""Private C14-only integration; preparation never executes CPU or VICE.

Root owns the candidate source and pure suites. This wrapper copies a frozen
product, seals/packages only C14, and reuses independent public/style oracles.
Native qualification owns8500/text8600 and discloses the public input seam.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,inspect,json,shutil,socket,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from bindings import verify
from overlays import wrap
from d81_image import D81Image
from overlay_catalog_policy import catalog_identity
BASE=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'
CANDIDATE=ROOT/'build/style-span-candidate/20261025T144206890856Z/production/styler.bin'
CANDIDATE_SHA='bd2a88b1f5d3406460517fd624f3822ca0bc634f4091b83340e9067302dd4b25'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(out,base,candidate):
 identity=json.loads((base/'freeze.json').read_text());assert len(identity['names'])==47
 assert sha(base/'build/editor.prg')==identity['prg_sha256']and sha(base/'build/supereditor.d81')==identity['disk_sha256']
 for name,digest in identity['assets'].items():assert sha(base/f'build/overlays/{name}.seo')==digest
 raw=candidate.read_bytes();assert sha(candidate)==CANDIDATE_SHA and len(raw)==4047
 older=ROOT/'build/style-span-candidate/20261025T143709808089Z/production/styler.bin';assert raw==older.read_bytes()
 bound=verify(base/'build/editor.prg',base/'build/editor.lbl');report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];assert s['se_overlay_managed_verification']==1 and s['se_overlay_capacity']==64
 old=(base/'build/overlays/styler.seo').read_bytes();assert old[5:7]==bytes([1,14])and len(old)-36==3923
 image=wrap(raw,1,14,int.from_bytes(old[10:12],'little'),api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(bound['digest']))
 private=out/'fixture';shutil.copytree(base,private);(private/'build/overlays/styler.seo').write_bytes(image)
 disk=private/'build/supereditor.d81';command=['c1541','-attach',str(disk),'-delete','styler','-write',str(private/'build/overlays/styler.seo'),'styler,s'];p=subprocess.run(command,capture_output=True,text=True);(out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
 before=D81Image((base/'build/supereditor.d81').read_bytes());after=D81Image(disk.read_bytes());assert after.read(b'STYLER',kind=1).data==image
 assert {e.name for e in before.entries()}=={e.name for e in after.entries()}
 for entry in before.entries():
  if entry.name!=b'STYLER':
   a,b=before.read(entry.name),after.read(entry.name);assert a.data==b.data and a.sectors==b.sectors,(entry.name,'nonC14 file changed')
 for name in identity['names']:
  if name!='styler':assert(private/f'build/overlays/{name}.seo').read_bytes()==(base/f'build/overlays/{name}.seo').read_bytes()
 pack=after.read(b'GEOSFONTS',kind=1).data;(private/'font-pack.bin').write_bytes(pack)
 project=candidate.parent.parent/'candidate-source/src/style/plan.s';assert project.is_file();source=project.read_bytes();zipbase=base/'product-sources.zip'
 shutil.copy2(zipbase,private/'baseline-product-sources.zip')
 with zipfile.ZipFile(zipbase)as original,zipfile.ZipFile(private/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as target:
  for name in original.namelist():target.writestr(name,source if name=='src/style/plan.s'else original.read(name))
 identity['assets']['styler']=hashlib.sha256(image).hexdigest();identity['disk_sha256']=sha(disk)
 identity.setdefault('sources',{})['src/style/plan.s']=hashlib.sha256(source).hexdigest();identity['private_C14_candidate']=dict(raw_sha256=sha(candidate),payload_bytes=4047,baseline_payload_bytes=3923,source_plan_sha256=hashlib.sha256(source).hexdigest(),candidate_path=str(candidate),base=str(base),no_other_product_change=True)
 (private/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 manifest=json.loads((private/'build/disk-manifest.json').read_text());manifest.update(disk=str(disk),sha256=sha(disk),private_replace_command=command,baseline_disk_sha256=sha(base/'build/supereditor.d81'));(private/'build/disk-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 shutil.copy2(candidate,out/'candidate-styler.bin');shutil.copy2(project,out/'candidate-plan.s');(out/'preparation.json').write_text(json.dumps(dict(status='prepared-only',private_fixture=str(private),base=str(base),candidate=identity['private_C14_candidate'],disk_sha256=identity['disk_sha256'],candidate_seo_sha256=identity['assets']['styler'],only_C14_payload_replaced=True,all_other_D81_files_bytes_and_sectors_exact=True,execution_requires_root_final_signal=True),indent=2)+'\n')
 return private


def adapt_oracles(fixture,out):
 import test_style_editor as style, test_grid_modes as grid, font_fixture
 assert json.loads((fixture/'build/editor-report.json').read_text())['symbols']['se_overlay_managed_verification']==1
 changes=[]
 def style_catalog(self):
  raw=self.read(self.s['se_overlay_ids'],8*self.s['se_overlay_capacity']);assert len(raw)==512
  return catalog_identity(raw[:384],self.s)+raw[384:] # preserve adjacent128B exactly
 def remove(self,identity,slot):
  i=next(i for i in range(self.s['se_overlay_capacity'])if self.m.read(self.s['se_overlay_ids']+i)==identity and(self.m.read(self.s['image_slot']+i)&0x7f)==slot)
  self.m.write(self.s['se_overlay_ids']+i,0);self.m.write(self.s['se_overlay_active']+slot,0);return i
 style.Fixture.catalog=style_catalog;style.Fixture.remove_asset=lambda self,slot,identity=14:remove(self,identity,slot);grid.Fixture.remove=remove
 old_font=font_fixture.install_font_pack
 font_fixture.install_font_pack=lambda f,pack=None:old_font(f,pack or fixture/'font-pack.bin')
 text=inspect.getsource(grid.run)
 old="[(1,'F8'),(2,'F8'),(0,'F8'),(2,'CTRL-F8'),(1,'CTRL-F8'),(0,'CTRL-F8')]"
 new="[(1,'F8'),(2,'F8'),(1,'CTRL-F8'),(0,'CTRL-F8')]"
 assert text.count(old)==1,'Review obsolete3mode wrap expectations before adapting'
 namespace=dict(vars(grid));exec(compile(text.replace(old,new),str(Path(__file__))+'::four-mode-compatible-grid','exec'),namespace)
 changes=[dict(scope='Style512Bcatalogguard',normalization='Only first384B publishedslotbit7 per managed policy; remaining128sessionbytes exact'),dict(scope='Missingasset selectors',change='capacity64 lookup andlow7slotbits; injectedID-removal protocol unchanged'),dict(scope='Historical3modewrap',original=old,replacement=new,reason='Currentmode3exists; validF8/CTRL-F8 routes retainedwithin40/60/80. No geometry/pixel/source/REU oracle removed.'),dict(scope='CPUfontimport',change='Exact same SHA/CRC-guarded actual FD provider/DMA, using immutable D81pack ratherthan changinglivebuild')]
 (out/'oracle-adaptations.json').write_text(json.dumps(dict(changes=changes,original_sha256={str(Path(m.__file__).relative_to(ROOT)):sha(Path(m.__file__))for m in [style,grid,font_fixture]}),indent=2)+'\n')
 return style,grid,namespace['run']


def cpu(out,fixture):
 style,grid,grid_run=adapt_oracles(fixture,out)
 a=out/'source40';a.mkdir();style.run(a,fixture)
 b=out/'grid60-80';b.mkdir();grid_run(b,fixture,True)
 result=dict(status='passed',source40=json.loads((a/'result.json').read_text()),grid=json.loads((b/'result.json').read_text()),scope='PrivateC14only actualroot source40/60/80 styles/pixels/cancel/foreignlease/owner1/modal/missingC14/R14/C15/24bit/pending/selection. Originalindependentoracles retained except recordedcatalogpolicy/obsolete3mode-input adaptations.')
 (out/'CPU-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def native_qualify(out,base,private):
 import test_display_timing_vice as timing, test_reu_capacity_vice as capacity
 import test_file_throughput_vice as io
 from test_fold_retention_vice import Captured
 import vice_plan
 class Plan(timing.Plan):
  def plan(self):
   p=super().plan();p['global_defaults']['monitor_port_start']=8500;p['global_defaults']['monitor_port_span']=1;assert not p['global_defaults'].get('kill_stale',False);return p
 def ports():
  for port in [8500,*range(8600,8640)]:
   with socket.socket()as sock:sock.bind(('127.0.0.1',port))
 results={};evidences={}
 for tag,source in [('baseline',base),('candidate',private)]:
  e=timing.native.freeze(source);target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-style-span-'+tag+'-native');shutil.move(e,target);e=target;io.unpack_catalog(e)
  n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.boot();n.open('open_diverse',b'DIVERSE');data=timing.native.live.grid.fixture();new=timing.native.live.grid.native_text('Q')+data
  for mode in [0,1,2]:
   n.typed('source_mode_'+str(mode),'mode '+str([40,60,80][mode]));n.typed('source_top_'+str(mode),'top')
   for field,value in [('se_st_valid',1),('se_st_request',0),('se_f_owner',0)]:n.memory('before_'+str(mode)+'_'+field,field,value)
   n.snapshot('m'+str(mode)+'-before',data,mode)
   n.measure('m'+str(mode)+'-typing',new,mode,key=timing.native.live.grid.native_text('Q')[0],category='settled-source-style-'+str([40,60,80][mode]))
   n.send('undo_'+str(mode),b'\x1a');n.memory('undo_length_'+str(mode),'se_v_length',len(data),3)
  plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n');initial=(e/'working.d81').read_bytes()
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;built=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(built.stdout+built.stderr);assert not built.returncode
  with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
   for folder in ['tests','tools']:
    for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
  ports();print('NATIVE',tag,e,'steps',len(n.steps),'captures6',flush=True);capacity.run_owned_plan(plan,n.out,timeout=1800);ports();result=timing.evaluate(n);assert(e/'working.d81').read_bytes()==initial,'read-onlystyle D81 changed'
  images=timing.native.live.grid.reu_images(n.out/'run');intervals=[]
  fonts={name:(e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)};catalog=timing.native.previous.pack_catalog((e/'font-pack.bin').read_bytes(),fonts['native8.bin'])
  for mode in [0,1,2]:
   ident='m'+str(mode);b=(n.out/'captures'/(ident+'-before-ram.bin')).read_bytes();a=(n.out/'captures'/(ident+'-typing-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-before-colors.bin')).read_bytes();f=Captured(n.s,b,colors,e);f.colored=True
   assert timing.native.live.merged(f,images[ident+'-before'])==data
   case=dict(source=data.hex(),mode=mode,folds=[],kind='literal',caret=0,mark=False,anchor=None)
   expected,attrs=capacity.raster(e,case,f,fonts,catalog)
   if mode:assert b[0x6000:0x7f40]==expected and b[0x4000:0x43e8]==attrs
   w,h,pixels=timing.read_png(n.out/('native-'+ident+'-before.png'));vx,vy=result['native_viewport'];palette={}
   for yy in range(200):
    for xx in range(320):
     attr=attrs[(yy//8)*40+xx//8];ink=expected[(yy//8)*320+(xx//8)*8+yy%8]&(128>>(xx%8));color=attr>>4 if ink else attr&15;pixel=pixels[(vy+yy)*w+vx+xx];assert pixel==palette.setdefault(color,pixel),(tag,mode,'beforeVICpixels',xx,yy)
   assert len(set(palette.values()))==len(palette)
   assert catalog_identity(a[n.s['se_overlay_ids']:n.s['se_overlay_ids']+384],n.s)==catalog_identity(b[n.s['se_overlay_ids']:n.s['se_overlay_ids']+384],n.s)
   state=lambda raw:raw[n.s['se_doc_roots']:n.s['se_doc_roots']+512]+b''.join(raw[n.s[k]:n.s[k]+w]for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_sel_mark',1),('se_clip_token',5),('se_clip_length',3)])
   assert state(b)==state(a),(tag,mode,'pendingtypingchangedcanonical/history')
   before=images[ident+'-before'];after=images[ident+'-typing'];assert len(before)==len(after)==16777216
   handle=a[n.s['se_gc_handle']]
   if mode:
    bank=a[n.s['se_reu_map']+handle];assert handle and bank and a[n.s['se_reu_logical_owner']+handle]==a[n.s['se_reu_physical_owner']+bank]==0xfe;lo=bank*65536;hi=lo+5280;assert before[:lo]==after[:lo]and before[hi:]==after[hi:]
   else:assert before==after
   intervals.append(dict(mode=mode,whole_REU_bytes=16777216,allowed_FE_prefix=5280 if mode else 0))
  (e/'native-guards.json').write_text(json.dumps(dict(status='passed',pending_canonical_intervals=intervals,read_only_D81=True),indent=2)+'\n');results[tag]=result;evidences[tag]=str(e)
 compare=[]
 for b,c in zip(results['baseline']['measurements'],results['candidate']['measurements']):
  assert b['id']==c['id'];bp=Path(evidences['baseline'])/'timing'/('native-'+b['id']+'.png');cp=Path(evidences['candidate'])/'timing'/('native-'+c['id']+'.png');assert bp.read_bytes()==cp.read_bytes(),(b['id'],'A/B PNG bytes differ')
  own=lambda row:sum(g['payload_self']for g in row['cost_profile']['groups']if(g['slot'],g['id'])==(1,14))
  compare.append(dict(id=b['id'],baseline_settled_cycles=b['emulated_cycles'],candidate_settled_cycles=c['emulated_cycles'],baseline_first_publication=b['first_publish_cycles'],candidate_first_publication=c['first_publish_cycles'],baseline_C14_self_cycles=own(b),candidate_C14_self_cycles=own(c),baseline_counters=b['counter_deltas'],candidate_counters=c['counter_deltas'],PNG_byte_identical=True))
 summary=dict(status='passed',evidences=evidences,cases=compare,scope='PrivateC14only native settledcost comparison; source/plan/pixels/catalog/payload/shim/nativefont/D81 guards. ExplicitPC/SPinputseam, no physicalkeylatency or worstcaseclaim.')
 (out/'native-result.json').write_text(json.dumps(summary,indent=2)+'\n');print('NATIVEPASS',json.dumps(summary),flush=True);return summary


def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--candidate',type=Path,default=CANDIDATE);p.add_argument('--prepare',action='store_true');p.add_argument('--prepared',type=Path);p.add_argument('--run-cpu',action='store_true');p.add_argument('--run-native',action='store_true');a=p.parse_args()
 if not(a.prepare or a.run_cpu or a.run_native):print('Preparation only bydefault. --prepare packagesprivateC14; --run-cpu onlyafterparentfinalsignal.');return
 if a.prepared:out=a.prepared.resolve();fixture=out/'fixture'
 else:
  out=ROOT/'build/style-span-editor-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);fixture=prepare(out,a.base.resolve(),a.candidate.resolve())
 print('PREPARED',out,flush=True)
 if a.run_cpu:cpu(out,fixture)
 if a.run_native:native_qualify(out,a.base.resolve(),fixture)
if __name__=='__main__':main()
