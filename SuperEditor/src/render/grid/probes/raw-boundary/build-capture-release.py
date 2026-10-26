"""Private retained-R25 capture entry; correction release remains immutable."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'agentsworking/evidence/M8/20261026T075817016189Z-grid-raw-boundary-fix'
WRAPPED=ROOT/'agentsworking/evidence/M8/20261026T074830577823Z-grid-raw-wrapped'
def build(out,full_crc=True):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 for p in(WRAPPED/'release/generated-sources.zip',BASE/'release/sources.zip'):
  with zipfile.ZipFile(p)as z:z.extractall(tree)
 d=tree/'src/render/grid/caret';spec=importlib.util.spec_from_file_location('capture_pair',d/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);base=BASE/'fixture';m.build(out/'control',base)
 for n in('grid','geostail'):assert(out/'control'/(n+'.seo')).read_bytes()==(base/'build/overlays'/(n+'.seo')).read_bytes(),n+' original differs'
 p=d/'caret.s';s=p.read_text()
 def replace(a,b):
  nonlocal s
  assert s.count(a)==1,a;s=s.replace(a,b)
 replace('.import se_overlay_ids,image_slot', '.import se_overlay_active\n.import se_overlay_ids,image_slot')
 replace(' lda #0\n sta C+63\n',' lda #0\n sta C+63\n sta C+62 ;capture-only retained R-slot catalogue index, zero before first admission\n')
 replace('capture:\n ; Trusted', 'capture:\n lda se_overlay_active\n sta C+62 ;actual checked R25 admission just returned; no intervening R-slot service\n ; Trusted')
 replace('helper:\n sta se_overlay_frame\n lda #25\n ldx #0\n jmp se_overlay_call\n','helper:\n sta se_overlay_frame\n ldx OP\n bne @ordinary\n ldx C+62\n beq @ordinary\n cpx se_overlay_active\n bne @ordinary\n ; Exclusive capture calls only resident source/CRC/DMA between helpers.\n ; The actual real-loader-admitted R25 remains at its public fixed entry.\n jmp $A010\n@ordinary:\n lda #25\n ldx #0\n jmp se_overlay_call\n')
 if full_crc:
  replace('.import se_crc_init,se_crc_byte,se_crc_value,', '.import se_crc_table_low,se_crc_table_high\n.import se_crc_init,se_crc_byte,se_crc_value,')
  replace(' lda se_overlay_active\n sta C+62 ;actual checked R25 admission just returned; no intervening R-slot service\n',' lda se_overlay_active\n sta C+62 ;actual checked R25 admission just returned; no intervening R-slot service\n jsr capture_tables\n')
  replace('packet_crc:\n lda #9\n jmp helper\n','packet_crc:\n lda OP\n bne @ordinary\n jsr se_crc_init\n ldy #0\n@byte:\n lda P,y\n eor se_crc_value+1\n tax\n lda se_crc_value\n eor $8E00,x\n sta se_crc_value+1\n lda $8D00,x\n sta se_crc_value\n iny\n cpy #240\n bcc @byte\n rts\n@ordinary:\n lda #9\n jmp helper\n')
  replace('authenticate_helper:\n','; Fresh data-only expansion in exclusively owned, lease-free CAPTURE phase.\n; Neither source peek nor R25 capture helpers use the legacy FS frame.\ncapture_tables:\n .assert (se_crc_table_low & $FF)=0,lderror,"resident half-table alignment"\n .assert se_crc_table_high=se_crc_table_low+128,lderror,"resident half-table layout"\n ldx #0\n@byte:\n lda se_crc_table_low,x\n sta $8D00,x\n eor #$88\n sta $8D80,x\n lda se_crc_table_high,x\n sta $8E00,x\n eor #$91\n sta $8E80,x\n inx\n bpl @byte\n rts\nauthenticate_helper:\n')

 p.write_text(s);m.build(out/'candidate',base);fixture=out/'fixture';shutil.copytree(base,fixture);ident=json.loads((fixture/'freeze.json').read_text());image=(out/'candidate/grid.seo').read_bytes();(fixture/'build/overlays/grid.seo').write_bytes(image);ident['assets']['grid']=hashlib.sha256(image).hexdigest();ident['private_change']='Capture only: reuse real-admitted unchanged R25 active slot entry, every owner/range/source/CRC check retained.';(fixture/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n')
 result=dict(status='built',base=str(base),changed=['grid'],newBSS=0,newZP=0,full_crc=full_crc,phase=[0x8d00,0x8f00]if full_crc else[],assets={n:ident['assets'][n]for n in('grid','geostail','viewsource')},grid=(out/'candidate/grid.map').read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip());(out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':
 import sys
 print(build(Path(sys.argv[1]).resolve())[1])
