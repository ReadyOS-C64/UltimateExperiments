"""Private real C6/R30/C32 two-color transaction. No canonical writes."""
from pathlib import Path
import sys,json,subprocess,binascii,re,zipfile
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent;R=D/'runtime';sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');seg={}
 def run(a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 def obj(name,path,flags=(),inc=None):
  o=out/(name+'.o');run(['ca65','-g','-I',out,'-I',R,'-I',D,'-I',inc or ROOT/'src','-o',o,*flags,path]);z=subprocess.check_output(['od65','--dump-segments',o],text=True);seg[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',z,re.S)};assert not any(seg[name].get(k,0)for k in('BSS','ZEROPAGE'));return o
 def link(tag,objects,cfg):
  run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(tag+'-aliases.s'),*objects]);a=obj(tag+'-aliases',out/(tag+'-aliases.s'));run(['ld65','-C',cfg,'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objects,a]);return(out/(tag+'.bin')).read_bytes()
 vectors={'se_gtt_admit':0xa020,'se_gtt_current':0xa023,'se_gp_cache_slot':0xa026,'se_gp_cache_read':0xa029,'se_gp_cache_write':0xa02c,'se_gcc_status':0xa02f,'se_tcb_two_check':0xa032}
 (out/'vectors.s').write_text('\n'.join('.export '+n+'\n'+n+'=$'+f'{v:04X}'for n,v in vectors.items())+'\n')
 stageobjects=[obj(n,R/(n+'.s'))for n in('stage-entry','transaction','prepare','wide','transform-stage')]+[obj('vectors',out/'vectors.s')]
 p=link('stage',stageobjects,R/'stage.cfg');raw=p[32:];assert len(raw)<=4064
 (out/'stage-constants.inc').write_text(f'GCT_STAGE_ID=32\nGCT_STAGE_OFFSET=32\nGCT_STAGE_LENGTH={len(raw)}\nGCT_STAGE_CRC=${binascii.crc_hqx(raw,65535):04X}\nGCT_STAGE_IMAGE_LENGTH={len(p)}\nGCT_STAGE_IMAGE_CRC=${binascii.crc_hqx(p,65535):04X}\nGCT_STAGE_VALID=$42\n')
 def seo(name,p,slot,ident):
  q=wrap(p,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/(name+'.seo')).write_bytes(q);return q
 images={'stage':seo('stage',p,1,32)}
 objs=[obj(n,R/(n+'.s'))for n in('supervisor','stage-guard','guard')]+[obj(n,ROOT/'src/render/geos/typing'/(n+'.s'))for n in('transfer','status-normal','status-raster')]+[obj('two-color',D/'two-color.s')]
 q=link('worker',objs,R/'supervisor.cfg');images['worker']=seo('worker',q,0,30);assert all(q[v]==0x4c for v in range(0x20,0x35,3))
 prod=out/'frozen';prod.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip') as z:
  for n in z.namelist():
   if n.startswith(('src/','assets/')) and not n.endswith('/'):
    t=prod/n;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(z.read(n))
 cert=prod/'src/render/geos/typing/certify.s';txt=cert.read_text();assert txt.count(' jsr neighbors\n jcs release')==1;txt=txt.replace('@bad:\n sec\n rts\n\n; Same full row bounds','@bad:\n lda T+3\n sta GTC_ROW\n sec\n rts\n\n; Same full row bounds');cert.write_text(txt.replace(' jsr neighbors\n jcs release',' jsr neighbors\n lda #0\n rol\n sta GTC_RESERVED ;CRC-bound conditionalneighborproof0/1'))
 # C6 editor imports require generated complete numeric aliases, unlike C32.
 api=(out/'editor-api.inc').read_bytes();run([sys.executable,ROOT/'tools/overlay_api.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc','--all-public','--symbols','object_owner','object_banks','object_size_lo','object_size_mid','object_size_hi','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry','text_ptr','screen_ptr'])
 w=link('window',[obj('window',prod/'src/overlays/hot-window.s',('-D','EDITOR_BINDINGS=1'),prod/'src'),obj('certify',cert,inc=prod/'src'),obj('window-transfer',prod/'src/render/geos/typing/transfer.s',inc=prod/'src')],ROOT/'cfg/overlay-c.cfg');images['window']=seo('window',w,1,6);(out/'editor-api.inc').write_bytes(api)
 result=dict(R30=len(q),C32=len(p),stage_raw=len(raw),C6=len(w),segments=seg,new_BSS=0,new_ZP=0,vectors=vectors,scope='Private actual C6 pending producer→sealed R30/C32 dry election before publication. No canonical/root/native promotion.');(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return images,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])
