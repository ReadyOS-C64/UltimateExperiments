"""Build sealed R30 supervisor and C32 local plain/styled typing capsule."""
from pathlib import Path
import sys,json,subprocess,binascii,re
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify

def build(out,base,variant='before'):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 seg={}
 def run(a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 def obj(name,path):
  o=out/(name+'.o');run(['ca65','-g','-I',out,'-I',D,'-I',ROOT/'src','-o',o,path]);z=subprocess.check_output(['od65','--dump-segments',str(o)],text=True);seg[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',z,re.S)};assert not any(seg[name].get(k,0)for k in('BSS','ZEROPAGE'));return o
 def link(tag,objects,cfg):
  run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(tag+'-aliases.s'),*objects]);a=obj(tag+'-aliases',out/(tag+'-aliases.s'));run(['ld65','-C',cfg,'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objects,a]);return(out/(tag+'.bin')).read_bytes()
 vectors={'se_gtt_admit':0xa020,'se_gtt_current':0xa023,'se_gp_cache_slot':0xa026,'se_gp_cache_read':0xa029,'se_gp_cache_write':0xa02c,'se_gcc_status':0xa02f}
 (out/'vectors.s').write_text('\n'.join('.export '+n+'\n'+n+'=$'+f'{v:04X}'for n,v in vectors.items())+'\n')
 stageobjects=[obj(n,(D/('transaction-'+variant+'.s') if n=='transaction' else D/(n+'.s')))for n in('stage-entry','transaction','prepare','wide','transform-stage')]+[obj('vectors',out/'vectors.s')]
 p=link('stage',stageobjects,D/'stage.cfg');raw=p[32:];assert len(raw)<=4064
 constants=f'GCT_STAGE_ID=32\nGCT_STAGE_OFFSET=32\nGCT_STAGE_LENGTH={len(raw)}\nGCT_STAGE_CRC=${binascii.crc_hqx(raw,65535):04X}\nGCT_STAGE_IMAGE_LENGTH={len(p)}\nGCT_STAGE_IMAGE_CRC=${binascii.crc_hqx(p,65535):04X}\nGCT_STAGE_VALID=$42\n'
 (out/'stage-constants.inc').write_text(constants)
 images={};images['stage']=wrap(p,1,32,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'stage.seo').write_bytes(images['stage'])
 objs=[obj(n,(D/('transaction-'+variant+'.s') if n=='transaction' else D/(n+'.s')))for n in('supervisor','stage-guard','guard')]+[obj(n,ROOT/'src/render/geos/typing'/(n+'.s'))for n in('transfer','status-normal','status-raster')]
 q=link('worker',objs,D/'supervisor.cfg');images['worker']=wrap(q,0,30,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'worker.seo').write_bytes(images['worker'])
 result=dict(R30=len(q),C32=len(p),stage_raw=len(raw),segments=seg,new_BSS=0,new_ZP=0,vectors=vectors,scope='C32 staged at5000; R30 helper-vector supervisor. C6 is built by the normal window target.')
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return images,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])
