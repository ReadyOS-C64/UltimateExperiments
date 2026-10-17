from pathlib import Path
import json,shutil
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
W=P/'project'
# The runtime-only inventory deliberately omits the older UNIT build's inputs.
# Copy that public native inventory and its missing inputs for default proofs.
source=ROOT/'build_support/native_media_sources.json'
f=W/'build_support/native_media_sources.json'
if not f.exists():shutil.copyfile(source,f)
native=json.loads(source.read_text())
for n in native['native'].values():
 d=W/n
 if not d.exists():d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,d)
added=['include/floppy_format.inc','src/floppy_format.s','src/floppy_format_check.s']
for name in ['runtime_media_sources.json','native_media_sources.json']:
 f=W/'build_support'/name;j=json.loads(f.read_text())
 if name=='runtime_media_sources.json':j['core']=sorted(set(j['core'])|set(added))
 else:
  for n in added:j['native']['work/'+n]=n
 f.write_text(json.dumps(j,indent=2)+'\n')
f=W/'tools/native_media/build_ui_bridge.py';s=f.read_text()
needle='role=ap.parse_args().role';assert needle in s
s=s.replace(needle,"ap.add_argument('--floppy-format',action='store_true');options=ap.parse_args();role=options.role")
needle="'DOS64_MEDIA_BINDING=1']";assert needle in s
s=s.replace(needle,"'DOS64_MEDIA_BINDING=1','DOS64_FLOPPY_FORMAT='+str(int(options.floppy_format))]")
lines=s.splitlines();idx=next(i for i,l in enumerate(lines)if l.startswith("run([sys.executable,'-B','build_support/verify_memory.py'"))
lines[idx]="memory_assets=[('--overlay-files','files'),('--overlay-render','render'),('--overlay-input','input'),('--overlay-pit','pit'),('--overlay-gfx','gfx'),('--overlay-hd','hd'),('--overlay-disk','disk'),('--shadow','hdb'),('--saver','saver'),('--import-code','import')]+([('--overlay-format','format')]if options.floppy_format else [])\nrun([sys.executable,'-B','build_support/verify_memory.py','build/dos64.map','build/dos64.labels',*sum(([flag,'build/dos64-resident.prg.'+suffix+'.bin'] for flag,suffix in memory_assets),[])],W)"
f.write_text('\n'.join(lines)+'\n')
f=W/'build_support/runtime_media.py';s=f.read_text()
s=s.replace('def build(out):','def build(out,floppy_format=False):')
needle="command=[str(Path(sys.executable).resolve()),'-B','build_ui_bridge.py','--role','runtime'];";assert needle in s
s=s.replace(needle,"command=[str(Path(sys.executable).resolve()),'-B','build_ui_bridge.py','--role','runtime']+(['--floppy-format']if floppy_format else []);")
s=s.replace("'flags':FLAGS,","'flags':dict(FLAGS,DOS64_FLOPPY_FORMAT=int(floppy_format)),")
needle='a=p.parse_args();r=build(a.out);';assert needle in s
s=s.replace(needle,"p.add_argument('--floppy-format',action='store_true',help='Enable XT360K FORMAT in the runtime-only profile');a=p.parse_args();r=build(a.out,floppy_format=a.floppy_format);")
f.write_text(s)
for n in ['build_support/runtime_media.py','tools/native_media/build_ui_bridge.py']:compile((W/n).read_text(),n,'exec')
print('Adapted optional source-only FORMAT builder and both native inventories')
