"""Private public-command minimizer for the registered stress B5 failure."""
from pathlib import Path
import sys,json,hashlib,gzip
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tests'))
import test_editor_soak as old
ROOT=old.ROOT
BASE=ROOT/'build/normal-row80-committed/20261026T193357856684Z/fixture'
CONTROL=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture'
def run(out):
 out.mkdir(parents=True,exist_ok=True);dll=old.runner(out);results=[]
 for label,base in [('R16',BASE),('946',CONTROL)]:
  ident=json.loads((base/'freeze.json').read_text());old.fold.geos.grid.editor_fixture.ROOT=old.fold.geos.grid.cpu_editor.ROOT=base;old.fold.geos.grid.editor_fixture.NAMES=old.fold.geos.grid.cpu_editor.NAMES=ident['names']
  f=old.fold.Fixture(out,base,dll,True);events=[]
  source=old.fold.geos.native_text(':::region Work\rEditable line here.\r:::end\rTail.\r');data=source
  try:
   old.fold.geos.Fixture.source(f,data,banks=1,physical=32)
   f.command(115);f.render();f.command(116);f.render();events.append('fold-all/unfold-all actual valid map')
   f.typed(old.fold.geos.native_text('goto 3'));f.command(2);f.command(2);at=f.get('se_hot_caret');assert at==data.index(b':::END')+2,(at,data)
   raw=old.fold.geos.native_text('Q');f.key(raw[0]);data=data[:at]+raw+data[at:];f.command(1);f.command(16);assert f.merged()==source;f.command(17);assert f.merged()==data;events.append('GOTO3 RIGHT RIGHT Q LEFT Undo Redo')
   before=f.reu();f.audit_begin();error=None
   try:f.render()
   except AssertionError as e:error=repr(e)
   f.audit_end(before,'render malformed region')
   actual=f.merged();assert actual==data and f.read(0xc600,1024)==f.shim
   result=dict(label=label,fixture=str(base),PRG=ident['prg_sha256'],D81=hashlib.sha256((base/'build/supereditor.d81').read_bytes()).hexdigest(),events=events,source=data.hex(),length=len(data),actual_source_sha256=hashlib.sha256(actual).hexdigest(),error=error,fields={n:f.get(n,w)for n,w in [('se_e_error',1),('se_e_job',1),('se_f_owner',1),('se_hot_pending',1),('se_ef_valid',1),('se_ef_active',1),('se_ef_operation',1),('se_doc_read_locks',1),('se_fs_owned',1),('se_ef_count',2)]})
   results.append(result);(out/'result.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(result),flush=True)
   if label=='R16' and error:
    (out/'failure-ram.bin').write_bytes(f.read(0,65536))
    with gzip.open(out/'failure-reu.bin.gz','wb',compresslevel=6) as z:z.write(f.reu())
  finally:dll.fr_end();f.m.close()
if __name__=='__main__':run(Path(sys.argv[1]))
