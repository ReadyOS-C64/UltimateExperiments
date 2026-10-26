"""Private mapped INLINE reader. Frozen packedcold54, no shared outputs."""
from pathlib import Path
import sys,importlib.util,json,subprocess,re,shutil,hashlib
ROOT=Path(__file__).resolve().parents[3]
def build(out,base):
 p=ROOT/'src/cache/splice-editor-probe/build.py';sp=importlib.util.spec_from_file_location('visible_build',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);images,patch=m.build(out,base)
 tree=out/'source';here=ROOT/'src/cache/splice-inline-probe';shutil.copytree(here,tree/'src/cache/splice-inline-probe',dirs_exist_ok=True)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];binding=report['resident_binding']['digest'];sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
 def link(tag,slot,ident,files):
  d=out/tag;d.mkdir();objs=[]
  for i,p in enumerate(files):
   o=d/f'{i}.o';subprocess.run(['ca65','-g','-I',out,'-I',tree/'src','-D','BCA_READONLY_OPEN=1','-D','I_SPARSE_INLINE=1','-o',o,p],check=True);objs.append(o)
  subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objs],check=True);subprocess.run(['ca65','-o',d/'aliases.o',d/'aliases.s'],check=True);objs.append(d/'aliases.o')
  cfg=d/'image.cfg';cfg.write_text(f'MEMORY {{ IMAGE:file=%O,start=${0xB000 if slot else 0xA000:04X},size=$1000; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro,optional=yes; }}')
  subprocess.run(['ld65','-C',cfg,'-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objs],check=True);raw=(d/'image.bin').read_bytes();assert len(raw)<=4096
  image=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(d/'image.seo').write_bytes(image);return image,dict(bytes=len(raw),free=4096-len(raw),sha256=hashlib.sha256(raw).hexdigest())
 # R35 keeps all original read-only map validation; producer-only publication
 # moves nowhere. C40 continues using its unchanged R34.
 t=(tree/'src/cache/splice-probe/transport.s').read_text()
 t=t.replace(' cmp #4\n jeq publish_begin\n cmp #5\n jeq publish_step\n','')
 t=t.replace(' cmp #8\n jeq raw_read\n',' cmp #8\n jeq raw_read\n cmp #9\n jeq inline_begin\n cmp #10\n jeq inline_step\n')
 start=t.index('; Event identity');end=t.index('; Read-only mappedquery')
 t=t[:start]+'''return:rts
request:
 sta BCA_OFFSET
 sty BCA_OFFSET+1
 stx BCA_LENGTH
 lda #0
 sta BCA_OFFSET+2
 rts
advance:
 inc S_PSTATE
 jmp pending
inline_begin:jmp se_bc_page_begin
inline_step:jmp bca_page_step
'''+t[end:]
 (out/'transport-inline.s').write_text(t)
 # Capture next/slots only from the header validated by the actual page service;
 # consumers may use it only after full payload CRC completion.
 t=(tree/'src/cache/arena/page.s').read_text();t=t.replace('.include "object/api.inc"','.include "object/api.inc"\n.include "cache/splice-inline-probe/api.inc"')
 needle=' jsr page_offset\n lda #64\n sta BCA_CURSOR';assert t.count(needle)==1
 t=t.replace(needle,''' lda BCA_KIND
 cmp #2
 bne @not_inline
 lda BC_IO+24
 jne bca_corrupt
 lda BC_IO+23
 jeq bca_corrupt
 sta I_SLOTS
 lda #0
 sta S_TEMP
 sta S_TEMP+1
 ldx I_SLOTS
@width:clc
 lda S_TEMP
 adc #10
 sta S_TEMP
 bcc :+
 inc S_TEMP+1
:dex
 bne @width
 lda S_TEMP
 cmp BCA_USED
 jne bca_corrupt
 lda S_TEMP+1
 cmp BCA_USED+1
 jne bca_corrupt
 CP BC_IO+29,I_NEXT,4
@not_inline:
'''+needle)
 (out/'page-inline.s').write_text(t)
 images['mappedinlineio'],rb=link('mappedinlineio',0,35,[out/'transport-inline.s',tree/'src/cache/arena/core.s',tree/'src/cache/arena/open.s',out/'page-inline.s'])
 t=(tree/'src/cache/splice-query-probe/selector.s').read_text().replace('.include "cache/splice-query-probe/api.inc"','.include "cache/splice-inline-probe/api.inc"\n.include "render/geos/inline.inc"')
 t=t.replace(' beq begin\n',' beq normal_begin\n',1).replace(' jeq begin\n',' jeq normal_begin\n',1)
 t=t.replace(' cmp #2\n jeq cancel',' cmp #3\n jeq source_begin\n cmp #4\n jeq normal_begin\n cmp #2\n jeq cancel',1)
 t=t.replace(' lda #SQ_ID\n',' lda #43\n',1).replace(' lda #34\n',' lda #35\n',1)
 t=t.replace('begin:\n','''normal_begin:
 lda se_bc_flags
 and #BC_PAGE_PROOF
 bne normal_fallback
 jsr begin
 bcs @return
 cmp #2
 bne @return
 lda se_render_caps
 cmp #1
 beq normal_fallback
 cmp #3
 beq normal_fallback
 lda #2
 clc
@return:rts
normal_fallback:
 lda #26
 sta $9135
 lda SQ_FRAME+GSEM_COUNT
 cmp #161
 beq @wide
 lda #0
 beq @op
@wide:lda #4
@op:sta $9136
 lda #1
 clc
 rts
source_begin:
 jsr begin
 bcs @return
 cmp #2
 bne @pending
 lda se_render_caps
 cmp #1
 beq @fallback
 cmp #3
 beq @fallback
 lda #2
 clc
 rts
@fallback:
 lda #26
 sta $9135
 lda #5
 sta $9136
 lda #1
 clc
 rts
@pending:
 lda #20
 sta I_RETURN
 lda #1
 clc
@return:rts
begin:
 lda SQ_FRAME+GSEM_COUNT
 cmp #162
 jcs inline_argument
 lda SQ_FRAME+GSEM_ROLE
 cmp #14
 jcs inline_argument
.ifdef I_SPARSE_INLINE
 ; Admission only: invalid/short geometry falls back to the real parser.
 sec
 lda SQ_FRAME+GSEM_END
 sbc SQ_FRAME+GSEM_BODY
 lda SQ_FRAME+GSEM_END+1
 sbc SQ_FRAME+GSEM_BODY+1
 tax
 lda SQ_FRAME+GSEM_END+2
 sbc SQ_FRAME+GSEM_BODY+2
 jcc miss
 bne @long
 cpx #16
 jcc miss
@long:
.endif
''',1)
 t=t.replace(' lda #0\n tax\n@clear:', ''' ldx #9
@save_roles:lda GI_OUTPUT_ROLES,x
 sta $9030,x
 dex
 bpl @save_roles
 lda #0
 tax
@clear:''',1)
 t=t.replace(' lda #1\n sta S_MODE',' lda #21\n sta I_RETURN\n lda #1\n sta S_MODE',1)
 t=t.replace('step:\n','''step:
 lda S_STATE
 cmp #9
 jcs inline_step
''',1)
 t=t.replace(' jsr release\n jmp publish',' jmp inline_begin',1)
 # Baseline root is a genuine cache fallback, never interpreted as mapped.
 a=t.index('legacy:\n');b=t.index('failed_stale:',a);t=t[:a]+'legacy:jmp inline_miss\n'+t[b:]
 a=t.index('\npublish:\n');t=t[:a]+'\n.include "cache/splice-inline-probe/consume.inc"\n'
 t=t.replace('($FF-BC_ACTIVE-BC_PAGE_PROOF)','($FF-BC_ACTIVE-BC_PAGE_PROOF-I_READ_PROOF)').replace('ora #BC_ACTIVE','ora #(BC_ACTIVE|I_READ_PROOF)').replace('and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)\n cmp #(BC_ARMED|BC_ACTIVE)','and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE|I_READ_PROOF)\n cmp #(BC_ARMED|BC_ACTIVE|I_READ_PROOF)')
 a=t.index('entry:\n');b=t.index('busy:lda',a)
 t=t[:a]+'''entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 cmp #1
 jeq step
 cmp #2
 jeq cancel
 lda se_render_caps
 cmp #1
 beq @kind
 cmp #3
 jne miss
@kind:
 lda se_overlay_frame
 jeq normal_begin
 cmp #3
 jeq source_begin
 cmp #4
 jeq normal_begin
 lda #$C0
 sec
 rts
'''+t[b:]
 (out/'mapped-inline.s').write_text(t)
 images['mappedinline'],cb=link('mappedinline',1,43,[out/'mapped-inline.s'])
 # Runtime dispatcher upper range+2, independently assembled from identical input.
 # 42 remains pending until it explicitly resumes C20/C21 or real C26.
 dispatch=(out/'dispatch-routed.s').read_text();assert 'cmp #42' in dispatch
 (out/'dispatch-routed.s').write_text(dispatch.replace('cmp #42','cmp #44').replace('and #($FF-BC_ACTIVE)','and #($FF-BC_ACTIVE-64)'))
 # Byte length/operand proof of original400? source assembly is same module.
 d=out/'dispatch-inline';d.mkdir();o=d/'dispatch.o';subprocess.run(['ca65','-g','-I',out,'-I',tree/'src','-o',o,out/'dispatch-routed.s'],check=True)
 subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',o],check=True);subprocess.run(['ca65','-o',d/'aliases.o',d/'aliases.s'],check=True)
 cfg=d/'image.cfg';cfg.write_text(f'MEMORY {{ IMAGE:file=%O,start=${s["se_geos_render"]:04X},size=$1000; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; }}');subprocess.run(['ld65','-C',cfg,'-o',d/'image.bin',o,d/'aliases.o'],check=True)
 before=(out/'dispatch-before/image.bin').read_bytes();after=(d/'image.bin').read_bytes();delta=[i for i,(a,b)in enumerate(zip(before,after))if a!=b];assert len(before)==len(after)and len(delta)==2
 patch['new']=44;extra=[]
 for i in delta:
  if s['se_geos_render']+i==patch['address']:assert before[i]==40 and after[i]==44
  else:
   assert before[i]==247 and after[i]==183
   extra.append(dict(address=s['se_geos_render']+i,old=247,new=183,scope='resident missing-worker/STOP clears scoped reader64'))
 # Reassemble the complete DMA module against its exact frozen BSS placement,
 # compare original code against packaged resident, then change only53 mask.
 def dma(tag,text,managed=True):
  d=out/tag;d.mkdir();p=d/'dma.s';p.write_text(text);o=d/'dma.o';subprocess.run(['ca65','-g','-I',out,'-I',tree/'src',*(['-D','EDITOR_MANAGED_CODE=1']if managed else[]),'-o',o,p],check=True)
  subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',o],check=True);subprocess.run(['ca65','-o',d/'aliases.o',d/'aliases.s'],check=True)
  cfg=d/'image.cfg';cfg.write_text(f'MEMORY {{ IMAGE:file=%O,start=${s["se_reu_copy"]:04X},size=$1000; STATE:file="",start=${s["se_reu_c64"]:04X},size=32; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; BSS:load=STATE,type=bss; }}');subprocess.run(['ld65','-C',cfg,'-o',d/'image.bin',o,d/'aliases.o'],check=True);return(d/'image.bin').read_bytes()
 text=(tree/'src/reu/dma.s').read_text();old=dma('dma-before',text);new=dma('dma-reader64',text.replace('($FF-BC_PAGE_PROOF)','($FF-BC_PAGE_PROOF-64)'))
 prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');at=s['se_reu_copy']-load+2;assert old==prg[at:at+len(old)]
 ix=[i for i,(a,b)in enumerate(zip(old,new))if a!=b];assert len(old)==len(new)and len(ix)==1 and old[ix[0]]==223 and new[ix[0]]==159
 extra.append(dict(address=s['se_reu_copy']+ix[0],old=223,new=159,scope='checked owner53 writes revoke PAGE32 and scoped reader64 before DMA'))
 patch['extra_patches']=extra
 generic_old=dma('dma-generic-before',text,False);generic_new=dma('dma-generic-after',text.replace('($FF-BC_PAGE_PROOF)','($FF-BC_PAGE_PROOF-64)'),False);assert generic_old==generic_new
 (out/'dma-generic-identity.json').write_text(json.dumps({'bytes':len(generic_old),'sha256':hashlib.sha256(generic_old).hexdigest(),'byte_identical':True},indent=2)+'\n')

 # Actual C26's SOURCE3 delegates only to our fail-closed worker; SOURCE5
 # remains byte-for-byte real legacy parser fallback, avoiding delegation loops.
 t=(tree/'src/render/geos/inline.s').read_text();needle='source_begin:\n';assert t.count(needle)==1
 t=t.replace(needle,needle+' lda se_bc_flags\n and #32\n bne :+\n lda #43\n sta $9135\n lda #3\n sta $9136\n lda #1\n clc\n rts\n:\n',1)
 t=t.replace('begin:\n ldx #0\n beq begin_common','begin:\n ldx #0\n jmp begin_common');(out/'inline-delegate.s').write_text(t)
 # C26 needs original named segments, not the generic private CODE config.
 # Link through exact frozen config and the unchanged actual parser.
 d=out/'inline-delegate';d.mkdir();oo=[]
 for i,p in enumerate((out/'inline-delegate.s',tree/'src/supermark/inline.s')):
  o=d/f'{i}.o';subprocess.run(['ca65','-g','-I',out,'-I',tree/'src',*[v for x in ['SE_EDITOR_CACHED_INLINE_SOURCE=1','SE_EDITOR_INLINE_NAVIGATION=1','SE_EDITOR_NAV_TARGETED=1','BCQ_EDITOR_ACTIVE=1','BCQ_PAGE_REUSE=1']for v in ('-D',x)],'-o',o,p],check=True);oo.append(o)
 subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*oo],check=True);subprocess.run(['ca65','-o',d/'aliases.o',d/'aliases.s'],check=True);oo.append(d/'aliases.o');subprocess.run(['ld65','-C',tree/'cfg/geos-editor-inline.cfg','-o',d/'image.bin','-Ln',d/'image.lbl',*oo],check=True)
 raw=(d/'image.bin').read_bytes();c26_bytes=len(raw);assert len(raw)<=4096;images['geosinln']=wrap(raw,1,26,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(d/'image.seo').write_bytes(images['geosinln'])
 # Final row styles are a separate real C21 normal/WIDE caller, not SOURCE.
 t=(out/'page-routed.s').read_text();needle='    lda #GI_ID\n    ldx #GI_BEGIN';assert t.count(needle)==1;t=t.replace(needle,'    lda #43\n    ldx #GI_BEGIN');(out/'page-inline-routed.s').write_text(t)
 d=out/'page-inline-routed';d.mkdir();oo=[]
 for i,p in enumerate((out/'page-inline-routed.s',tree/'src/render/geos/cache.s')):
  o=d/f'{i}.o';subprocess.run(['ca65','-g','-I',out,'-I',tree/'src','-o',o,p],check=True);oo.append(o)
 subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*oo],check=True);subprocess.run(['ca65','-o',d/'aliases.o',d/'aliases.s'],check=True);oo.append(d/'aliases.o');subprocess.run(['ld65','-C',tree/'cfg/geos-editor-page.cfg','-o',d/'image.bin','-Ln',d/'image.lbl',*oo],check=True)
 raw=(d/'image.bin').read_bytes();assert len(raw)==4092;images['geospage']=wrap(raw,1,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(d/'image.seo').write_bytes(images['geospage'])
 # C23 authenticates C26 size/CRC before navigation. Rebuild and compare its
 # original image first; refresh this actual witness for the private C26 only.
 def nav(tag,raw_path):
  subprocess.run([sys.executable,tree/'tools/checkpoint_witness.py',raw_path,out,'--profile','navigation'],check=True)
  d=out/tag;d.mkdir();oo=[]
  for i,p in enumerate((tree/'src/render/geos/navigation.s',tree/'src/render/geos/cache-paint.s')):
   o=d/f'{i}.o';subprocess.run(['ca65','-g','-I',out,'-I',tree/'src','-o',o,p],check=True);oo.append(o)
  subprocess.run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*oo],check=True);subprocess.run(['ca65','-o',d/'aliases.o',d/'aliases.s'],check=True);oo.append(d/'aliases.o')
  subprocess.run(['ld65','-C',tree/'cfg/geos-editor-navigation.cfg','-o',d/'image.bin','-Ln',d/'image.lbl',*oo],check=True);return(d/'image.bin').read_bytes()
 old=nav('navigation-before',out/'geosinln/image.bin');assert old==(base/'build/overlays/geosnav.seo').read_bytes()[36:]
 raw=nav('navigation-private-witness',out/'inline-delegate/image.bin');assert len(raw)==len(old)
 images['geosnav']=wrap(raw,1,23,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(out/'navigation-private-witness/image.seo').write_bytes(images['geosnav'])
 (out/'inline-budget.json').write_text(json.dumps({'R35':rb,'C43':cb,'C26':c26_bytes,'C23':len(raw),'new_BSS':0,'new_ZP':0,'new_global_bytes':0,'scoped_revocation_bit':64,'admission':{'minimum_BODY_bytes':4096,'maximum_authenticated_events':8},'patch':patch},indent=2)+'\n');return images,patch
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
