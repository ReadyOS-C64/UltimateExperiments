"""Private byte-identical R21 control plus bounded uniform-role vote candidate."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[5]
def command(*a):return subprocess.run(list(map(str,a)),capture_output=True,text=True,check=True)
def build(out,base,candidate):
 out.mkdir(parents=True);tree=out/'tree'
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(tree)
 for n in('bsw9-original.bin','bsw9-widths.bin','bsw9.bin'):
  p=tree/'assets/fonts/generated'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/'fonts'/n,p)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];binding=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_f_owner\n.importzp text_ptr,screen_ptr\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 row=tree/'src/render/geos/literal-byte/row.s'
 if candidate:
  text=row.read_text();text=text.replace('roles_seen=P+39','roles_and=P+40\nroles_seen=P+39')
  text=text.replace('    sta roles_seen\n    ; Validate', '    sta roles_seen\n    lda #15\n    sta roles_and\n    ; Validate')
  text=text.replace('clear_slot-se_geos_row=$93','clear_slot-se_geos_row=$8C')
  text=text.replace('    ora roles_seen\n    sta roles_seen','    ora roles_seen\n    sta roles_seen\n    lda role\n    and roles_and\n    sta roles_and')
  text=text.replace('    beq @palette ;only actual role0 ink since reset; complete histogram retained','''    beq @palette ;actual role0 votes retained
    cmp roles_and
    bne @mixed
    ; OR==AND proves every actual glyph has this one role; append starts
    ; OR80 and can never enter here. Zero votes still elect defaultrole0.
    jsr histogram_address ;role is the last actual glyph, necessarily the uniform role
    ldy #0
    lda (se_gg_context),y
    beq @palette
    lda role
    sta best
    bne @palette
@mixed:''')
  if str(candidate).startswith('vertical'):
   text=row.read_text().replace('roles_seen=P+39','vertical_end=P+41\n.assert GR_PRIVATE+42<=GR_SIZE,error,"vertical scratch outside caller frame"\nroles_seen=P+39')
   old='''@slow:
    lda #0
    sta gy
@glyph_y:
    lda origin
    clc
    adc gy
    ldx origin
    bpl @positive
    jcc @skip_y
@positive:
    cmp F+GR_TOP
    jcc @skip_y
    cmp F+GR_BOTTOM
    jcs @skip_y
    sta sy
'''
   new='''@slow:
    ; Certified origin-8..7 and top/bottom0..8 yield signed differences
    ; -7..16. Intersect once, never index an ungenerated glyph raster row.
    lda F+GR_TOP
    sec
    sbc origin
    bpl :+
    lda #0
:   sta gy
    lda F+GR_BOTTOM
    sec
    sbc origin
    bmi @advance_glyph
    cmp #10
    bcc :+
    lda #9
:   sta vertical_end
    cmp gy
    bcc @advance_glyph
    beq @advance_glyph
    lda origin
    clc
    adc gy
    sta sy
@glyph_y:
'''
   assert old in text;text=text.replace(old,new,1)
   old='''@skip_y:
    inc gy
    lda gy
    cmp #9
    jcc @glyph_y
    clc'''
   new='''@skip_y:
    inc sy
    inc gy
    lda gy
    cmp vertical_end
    jcc @glyph_y
@advance_glyph:
    clc'''
   assert old in text;text=text.replace(old,new,1)
  else:
   text=text.replace('    .repeat 8\n        sta (se_gg_pointer),y','    .repeat 4\n        sta (se_gg_pointer),y',1)
  text=text.replace('    jsr glyph\n    jcs return\n    lda #0\n    sta byte_ok','    jsr glyph\n    jcs return\n    sta byte_ok ;actual glyph success returnsA0',1)
  text=text.replace('    adc subtotal\n    ldy #0\n    clc\n    adc (se_gg_context),y','    adc subtotal ;nibble sums<=8, therefore carry alreadyclear\n    ldy #0\n    adc (se_gg_context),y',1)
  text=text.replace('    pha\n    and #15\n    tax\n    lda popcount,x\n    sta subtotal\n    pla','    tax\n    and #15\n    tay\n    lda popcount,y\n    sta subtotal\n    txa',1)
  if candidate=='vertical-zero':
   text=text.replace('    adc subtotal ;nibble sums<=8, therefore carry alreadyclear\n    ldy #0','    adc subtotal ;nibble sums<=8, therefore carry alreadyclear\n    beq @no_votes\n    ldy #0',1)
   text=text.replace(':   sta (se_gg_context),y\n    ldy fragment',':   sta (se_gg_context),y\n@no_votes:\n    ldy fragment',1)
  row.write_text(text)
  changes=[]
  files=['src/render/geos/literal-byte/row.s','src/render/geos/literal-byte/measure.s','src/render/geos/literal-byte/glyph.s']
  for rel in files:
   p=tree/rel;lines=p.read_text().splitlines(True);owner=row if rel.endswith('row-validate.s')else p
   for i,line in enumerate(lines):
    op=line.strip().split(' ',1)[0]
    if op not in('jeq','jne','jcc','jcs','jmi','jpl'):continue
    trial=lines.copy();trial[i]=line.replace(op,'b'+op[1:],1);p.write_text(''.join(trial))
    try:command('ca65','-g','-I',out,'-I',tree/'src','-o',out/'short-proof.o',owner)
    except subprocess.CalledProcessError:continue
    lines=trial;changes.append(dict(file=rel,line=i+1,before=line.strip(),after=trial[i].strip()))
   p.write_text(''.join(lines))
  (out/'short-branches.json').write_text(json.dumps(changes,indent=2)+'\n')
 objects=[];paths=['src/render/geos/editor-row-entry.s']+[f'src/render/geos/literal-byte/{n}.s'for n in('row','measure','glyph','assets')]
 for i,path in enumerate(paths):
  obj=out/(str(i)+'.o');command('ca65','-g','-I',out,'-I',tree/'src','-o',obj,tree/path);objects.append(obj)
 command(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects);command('ca65','-o',out/'aliases.o',out/'aliases.s');objects.append(out/'aliases.o')
 try:command('ld65','-C',tree/'cfg/geos-editor-row.cfg','-o',out/'image.bin','-Ln',out/'image.lbl','-m',out/'image.map',*objects)
 except subprocess.CalledProcessError as e:print(e.stderr,flush=True);raise
 payload=(out/'image.bin').read_bytes();labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'image.lbl').read_text())};assert labels['se_geos_packed']==0xabf3 and labels['se_geos_widths']==0xaedb and labels['row_clear']==0xaf5b
 sealed=(base/'build/overlays/geosrow.seo').read_bytes()[36:]
 assert payload[0xBF3:0xF5B]==sealed[0xBF3:0xF5B], 'immutable fonts changed'
 if not candidate:assert payload==sealed
 (out/'build.json').write_text(json.dumps(dict(candidate=candidate,payload=len(payload),source=hashlib.sha256(row.read_bytes()).hexdigest()),indent=2)+'\n')
 return tree,s,labels,payload
if __name__=='__main__':build(Path(sys.argv[1]),Path(sys.argv[2]),('vertical'if sys.argv[3]=='vertical'else bool(int(sys.argv[3]))))
