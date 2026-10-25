from pathlib import Path
import sys,json,subprocess,binascii,re
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];(out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');objects=[]
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 for name,source,defs in [('stage-entry','stage-entry',[]),('lex-paint','lex-paint',[]),('lexer','lexer',['-D','SE_SM_CODE_ONLY=1']),('state','lexer',['-D','SE_SM_STATE_ONLY=1'])]:
  obj=out/(name+'.o');run(['ca65','-g','-I',out,'-I','src','-o',obj,*defs,(ROOT/'src/supermark/lexer.s' if source=='lexer' else ROOT/'src/render/geos/code-typing'/(source+'.s'))]);objects.append(obj)
 run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C','src/render/geos/code-typing/stage.cfg','-o',out/'stage.bin','-Ln',out/'stage.lbl','-m',out/'stage.map',*objects,out/'aliases.o'])
 payload=(out/'stage.bin').read_bytes();labels={p[2].lstrip('.'):int(p[1],16)for line in(out/'stage.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};assert labels['__CODE_LOAD__']==0xb020 and labels['se_gct_stage_lex']==0x5000 and labels['se_gct_stage_paint']==0x5003
 raw=payload[32:];assert len(raw)<4096 and len(payload)<=4096;crc=binascii.crc_hqx(raw,65535);fullcrc=binascii.crc_hqx(payload,65535)
 (out/'stage.seo').write_bytes(wrap(payload,1,31,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d)))
 constants=f'GCT_STAGE_ID=31\nGCT_STAGE_OFFSET=32\nGCT_STAGE_LENGTH={len(raw)}\nGCT_STAGE_CRC=${crc:04X}\nGCT_STAGE_IMAGE_LENGTH={len(payload)}\nGCT_STAGE_IMAGE_CRC=${fullcrc:04X}\nGCT_STAGE_LEX=$5000\nGCT_STAGE_PAINT=$5003\nGCT_STAGE_VALID=$41\nGCT_STAGE_STAMP=$5FE0\n'
 (out/'stage-constants.inc').write_text(constants);result=dict(payload_bytes=len(payload),raw_bytes=len(raw),raw_CRC=crc,full_CRC=fullcrc,run=0x5000,source_offset=32,jumps=dict(lex=0x5000,paint=0x5003),newBSS=0,newZP=0);(out/'stage.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
