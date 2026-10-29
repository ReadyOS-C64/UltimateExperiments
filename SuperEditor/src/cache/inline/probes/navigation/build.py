"""Private exact54 source clones; no canonical edits or shared build."""
from pathlib import Path
import binascii,hashlib,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[5];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
from test_cache_query import command
from overlays import wrap

def build(out,base,targeted=False):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith(('src/','cfg/'))and not n.endswith('/'):
    p=tree/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 report=base/'build/editor-report.json';r=json.loads(report.read_text());s=r['symbols'];digest=r['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def link(tag,paths,cfg,defs=()):
  d=out/tag;d.mkdir();objects=[]
  for i,path in enumerate(paths):
   obj=d/(str(i)+'.o');command('ca65','-g','-I',out,'-I',tree/'src','-I',HERE,*[v for x in defs for v in('-D',x)],'-o',obj,path);objects.append(obj)
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objects);command('ca65','-o',d/'aliases.o',d/'aliases.s');objects.append(d/'aliases.o');(d/'image.cfg').write_text(cfg);command('ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects);return(d/'image.bin').read_bytes()
 cfginline='MEMORY { IMAGE:file=%O,start=$B000,size=$1000,type=rw; PHASE:file="",start=$8D00,size=$01E0,type=rw; } SEGMENTS { GEOS_INLINE:load=IMAGE,type=ro; SM_INLINE:load=IMAGE,type=ro; SM_STATE:load=PHASE,type=bss,define=yes; }'
 inline=tree/'src/render/geos/inline.s';parser=tree/'src/supermark/inline.s';control=link('inline-control',[inline,parser],cfginline,('SE_EDITOR_CACHED_INLINE_SOURCE=1',));assert control==(base/'build/overlays/geosinln.seo').read_bytes()[36:]
 text=inline.read_text();text=text.replace(' lda se_overlay_frame\n cmp #GI_BEGIN_WIDE', ' lda se_overlay_frame\n.ifdef SE_EDITOR_INLINE_NAVIGATION\n cmp #6\n jeq nav_select\n cmp #7\n jeq nav_query_ready\n.endif\n cmp #GI_BEGIN_WIDE',1);text+='\n.ifdef SE_EDITOR_INLINE_NAVIGATION\n.include "helpers.inc"\n.endif\n';inline.write_text(text)
 default=link('inline-default',[inline,parser],cfginline,('SE_EDITOR_CACHED_INLINE_SOURCE=1',));assert default==control
 candidate=link('inline-candidate',[inline,parser],cfginline,('SE_EDITOR_CACHED_INLINE_SOURCE=1','SE_EDITOR_INLINE_NAVIGATION=1','BCQ_EDITOR_ACTIVE=1','BCQ_PAGE_REUSE=1')+(('SE_EDITOR_NAV_TARGETED=1',)if targeted else()))
 (out/'nav-witness.inc').write_text(f'NAV_SIZE={len(candidate)}\nNAV_CRC={binascii.crc_hqx(candidate,65535)}\n')
 seed=(base/'build/overlays/geossema.seo').read_bytes()[36:];(out/'seed-witness.inc').write_text(f'SEED_SIZE={len(seed)}\nSEED_CRC={binascii.crc_hqx(seed,65535)}\n')
 nav=tree/'src/render/geos/navigation.s';cache=tree/'src/render/geos/cache.s';cfgnav='MEMORY { IMAGE:file=%O,start=$B000,size=$1000,type=rw; } SEGMENTS { GEOS_NAVIGATION:load=IMAGE,type=ro; CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro,optional=yes; }';normal=link('navigation-control',[nav,cache],cfgnav);assert normal==(base/'build/overlays/geosnav.seo').read_bytes()[36:]
 original_text=nav.read_text();text=original_text;text=text.replace('.include "seed-witness.inc"','.include "seed-witness.inc"\n.include "nav-witness.inc"\n.include "cache/api.inc"')
 text=text.replace(' cmp #8\n jeq local_seed_ready',' cmp #9\n jeq nav_query_ready\n cmp #10\n jeq metric_ready\n cmp #8\n jeq local_seed_ready',1)

 text=text.replace('@query:\n NAV_COPY24 GN_SCAN,GSEM_FRAME+GSEM_QUERY\n lda #5\n sta GN_STATE\n lda #GSEM_ID\n ldx #GSEM_BEGIN\n jmp request','@query:\n NAV_COPY24 GN_SCAN,GSEM_FRAME+GSEM_QUERY\n lda GN_COMMAND\n cmp #47\n jne nav_legacy\n lda GN_FLAGS\n and #2\n jne nav_legacy\n jsr nav_selector_cap\n bcc :+\n rts\n:\n lda #9\n sta GN_STATE\n lda #26\n ldx #6\n jmp request\nnav_legacy:\n lda #5\n sta GN_STATE\n lda #GSEM_ID\n ldx #GSEM_BEGIN\n jmp request\nnav_query_ready:\n ldx #7\n bne nav_control',1)
 text=text.replace('nav_query_ready:\n ldx #7\n bne nav_control','nav_query_ready:\n lda #26\n ldx #7\n jmp request',1)
 # Share existing exact managed-image checker rather than add a second scanner.
 text=text.replace('local_seed_cap:\n ldx #0','local_seed_cap:\n ldy #0\n beq cap_common\nnav_selector_cap:\n ldy #5\ncap_common:\n ldx #0',1)
 for old,new in [('cmp #24\n bne @advance','cmp cap_table,y\n bne @advance'),('cmp #<SEED_SIZE','cmp cap_table+1,y'),('cmp #>SEED_SIZE','cmp cap_table+2,y'),('cmp #<SEED_CRC','cmp cap_table+3,y'),('cmp #>SEED_CRC','cmp cap_table+4,y')]:text=text.replace(old,new,1)
 text=text.replace('@bad:\n sec\n rts\ncache_query:','@bad:\n lda #$90\n sec\n rts\ncache_query:',1)
 text+='\ncap_table:.byte 24,<SEED_SIZE,>SEED_SIZE,<SEED_CRC,>SEED_CRC,26,<NAV_SIZE,>NAV_SIZE,<NAV_CRC,>NAV_CRC\n';nav.write_text(text)
 # Every retained short branch is proven in-range by ca65 against the final
 # private source. No guard/return is removed; imported targets remain long.
 short=[];lines=text.splitlines(True)
 for i,line in enumerate(lines):
  op=line.strip().split(' ',1)[0]
  if op not in('jeq','jne','jcc','jcs','jmi','jpl'):continue
  trial=lines.copy();trial[i]=line.replace(op,'b'+op[1:],1);nav.write_text(''.join(trial))
  try:command('ca65','-g','-I',out,'-I',tree/'src','-I',HERE,'-o',out/'short-proof.o',nav)
  except subprocess.CalledProcessError:continue
  lines=trial;short.append(dict(line=i+1,before=line.strip(),after=trial[i].strip()))
 nav.write_text(''.join(lines));(out/'short-branches.json').write_text(json.dumps(short,indent=2)+'\n')
 navraw=link('navigation-candidate',[nav,cache],cfgnav,('SE_GP_CACHE_WARM_ONLY=1','SE_GP_CACHE_READ_ONLY=1'))
 for name,raw,ident in [('geosinln',candidate,26),('geosnav',navraw,23)]:
  (out/(name+'.seo')).write_bytes(wrap(raw,1,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest)))
 dispatch=tree/'src/render/geos/dispatch.s';cfgresident=f'MEMORY {{ IMAGE:file=%O,start=${s["se_geos_render"]:04X},size=$1000,type=rw; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; }}';dr=link('dispatch-control',[dispatch],cfgresident);prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');assert dr==prg[2+s['se_geos_render']-load:2+s['se_geos_render']-load+len(dr)]
 text=dispatch.read_text();old='    and #1\n    bne :+\n    sta se_f_owner';new='    and #1\n    bne worker_complete\n    sta se_f_owner';assert text.count(old)==1;text=text.replace(old,new);dispatch.write_text(text);dc=link('dispatch-candidate',[dispatch],cfgresident);assert len(dc)==len(dr);assert sum(a!=b for a,b in zip(dc,dr))==1
 result=dict(control_inline=len(control),candidate_inline=len(candidate),control_navigation=len(normal),candidate_navigation=len(navraw),binding=digest);(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);return result

if __name__=='__main__':
 try:build(Path(sys.argv[1]),Path(sys.argv[2]))
 except subprocess.CalledProcessError as e:print(e.stderr,flush=True);raise
