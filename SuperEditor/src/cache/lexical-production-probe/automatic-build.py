"""Private automatic profile. No product registration or shared build writes.

Bit128 is a PRIVATE first-eligible-per-baseline attempt latch; bit64 remains
reserved. All generated sources are retained beside the private link maps.
"""
from pathlib import Path
import hashlib, importlib.util, json, sys, zipfile
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests')]
from test_cache_lexical import command,labels
D=Path(__file__).parent
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def once(t,a,b):
 assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)

def build(out,base):
 out.mkdir(parents=True)
 pinned={
 'src/cache/lexical-probe/worker.s':'5b48f9fb833cf8502bb287626f399b103233156f46bc143b229778cc1cd10e7b',
 'src/cache/lexical-probe/page.s':'206d00e1d50b22b8c2bcdd9b352552691c64d1d8ca73eaffab8e3d2304aa8621',
 'src/cache/lexical-link-probe/entry.s':'e44397419d282fde4773d4a78ad46d9e091ebb0aaae6df56afaaff6c830c3258',
 'src/cache/lexical-link-probe/guard.inc':'3f40f9cea65c3bd6f7d146e569d3de084f0d3b2762fdda9eeb0f6d08cb93cd47',
 'src/cache/lexical-admission-probe/build.py':'892cf8ef9f5d541b338b23830baf46360c708614de09bd55c6512f241bcc17ab'}
 for name,digest in pinned.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 b,l,r=module('auto_admission',ROOT/'src/cache/lexical-admission-probe/build.py').build(out/'admission',base)
 tree=out/'admission/adaptive/profiles/tree';report=base/'build/editor-report.json';digest=json.load(open(report))['resident_binding']['digest']
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  arena={n:z.read('src/cache/arena/'+n+'.s').decode()for n in ('core','open','page')}
  lexer=z.read('src/supermark/lexer.s').decode()
 def link(tag,sources,addr='$B000',segs=('CODE','RODATA'),state='$8D5E'):
  d=out/tag;d.mkdir();objects=[]
  (d/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  if tag in ('query','forward'):
   incq=d/'cache/query';incq.mkdir(parents=True)
   original=out/'admission/adaptive/profiles'/('lex35-compact'if tag=='query'else'lex37-compact')/'cache/query'
   for n in ('api.inc','proof-api.inc','proof.inc'):(incq/n).write_bytes((original/n).read_bytes())
  # Only C45 owns this completion include; normal C25 remains strict.
  inc=d/'render/geos';inc.mkdir(parents=True)
  h=(tree/'src/render/geos/preview-handoff.inc').read_text()
  if tag=='gateway':h=once(h,'@ordinary:\n lda #0\n clc\n rts','@ordinary:\n lda #21\n sta $9135\n lda #1\n sta $9136\n clc\n rts')
  (inc/'preview-handoff.inc').write_text(h)
  for n,t,defs in sources:
   p=d/(n+'.s');p.write_text(t);obj=d/(n+'.o');command(['ca65','-g','-I',d,'-I',tree/'src','-I',ROOT/'src',*[v for de in defs for v in ('-D',de)],'-o',obj,p]);objects.append(obj)
  command(['python3',ROOT/'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objects]);command(['ca65','-o',d/'aliases.o',d/'aliases.s'])
  (d/'image.cfg').write_text('MEMORY {C:file=%O,start='+addr+',size=$1000;S:file="",start='+state+',size=60;} SEGMENTS {'+''.join(n+':load='+('S,type=bss;'if n=='SM_STATE'else'C,type=ro;')for n in segs)+'}')
  command(['ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects,d/'aliases.o'])
  raw=(d/'image.bin').read_bytes();assert len(raw)<=4096 and raw[:16]==bytes.fromhex(digest)
  b[tag]=raw;l[tag]=labels(d/'image.lbl');r[tag]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());print('AUTO_FIT',tag,r[tag],flush=True)
  return raw
 # Per-CR completion is only an advisory load gate. It is published from the
 # checked CR AFTER classification, in the former parser-only USED byte.
 defs=['BCQ_EDITOR_ACTIVE=1','BCQ_CLASSIFY=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_PAGE_REUSE=1','BCQ_FORWARD_SEED=1','BCQ_COMMITTED_IDENTITY=1','BCQ_EMPTY_INLINE_HINT=1']
 for tag,forward in [('query',False),('forward',True)]:
  old=out/'admission/adaptive/profiles'/('lex37-compact'if forward else'lex35-compact');sources=[]
  names=['fast-entry'if forward else'classify-entry','query','source','records']
  for n in names:
   t=(old/('query-'+n+'.s')).read_text()
   if n==names[0]:t=once(t,'publish:\n','publish:\n lda BQ_CR+2\n and #$10\n sta F+GSEM_USED\n')
   if n=='records':
    a=t.index('@record_good:\n');e=t.index('@kind:\n',a);part=t[a:e]
    assert part.count(' jne bq_corrupt')==3
    t=t[:a]+part.replace(' jne bq_corrupt',' bne @record_bad')+t[e:]
   sources.append((n,t,defs+(['BCQ_FORWARD_QUERY=1']if forward else[])))
  for n in (['core','page']if forward else['core','open','page']):sources.append(('arena-'+n,(old/('arena-'+n+'.s')).read_text(),['BCA_READONLY_OPEN=1']))
  link(tag,sources)
 # Strict C25 keeps all old argument/context/range guards. Advisory hints only
 # avoid an unnecessary gateway load; R36 authenticates every actual hit.
 strict=(out/'admission/strict/strict.s').read_text()
 strict=once(strict,' lda $8BA8\n cmp #$81\n bne begin',' lda se_bc_flags\n bpl @may_build\n lda F+GSEM_USED\n and #$10\n beq begin\n@may_build:')
 # Measured cold construction loses at256/512, wins at768 in this bounded
 # workload. TAX preserves the SUB24 borrow into the high-byte subtraction.
 strict=once(strict,''' lda F+GSEM_END+1
 sbc F+GSEM_BODY+1
 bne @long
 lda F+GSEM_END+2
 sbc F+GSEM_BODY+2
 beq begin''',''' lda F+GSEM_END+1
 sbc F+GSEM_BODY+1
 tax
 lda F+GSEM_END+2
 sbc F+GSEM_BODY+2
 bne @long
 cpx #3
 bcc begin''')
 strict=once(strict,' ldx #2\n@copy_length:lda se_fs_length,x\n sta GLEX_LENGTH,x\n dex\n bpl @copy_length\n','')
 strict=once(strict,'@copy:lda F+GSEM_QUERY,x','@copy:lda se_fs_length,x\n sta GLEX_LENGTH,x\n lda F+GSEM_QUERY,x')
 link('strict',[('strict',strict,[]),('lexer',lexer,['SE_SM_CODE_ONLY=1']),('state',lexer,['SE_SM_STATE_ONLY=1'])],segs=('GEOS_SEMANTIC_LEX','SM_LEXER','SM_STATE'),state='$8D00')
 # Resolver is a genuine checked root/CR lookup with the borrowed C45 lease.
 # Remove unreachable COW writer states, not any checks on reachable reads.
 resolver=(out/'admission/adaptive/released/resolver.s').read_text()
 resolver=once(resolver,' cmp #BC_ARMED',' cmp #(BC_ARMED|BC_ACTIVE)') if ' cmp #BC_ARMED' in resolver else resolver
 # guard.inc is included separately, so inline the owned-active variant.
 guard=(ROOT/'src/cache/lexical-link-probe/guard.inc').read_text();guard=once(guard,' cmp #BC_ARMED',' cmp #(BC_ARMED|BC_ACTIVE)')
 resolver=once(resolver,'.include "cache/lexical-link-probe/guard.inc"',guard)
 a=resolver.index('find:\n');e=resolver.index('record_offset:\n',a);resolver=resolver[:a]+resolver[e:]
 a=resolver.index('record_write:\n');e=resolver.index('page_offset:\n',a);resolver=resolver[:a]+resolver[e:]
 a=resolver.index('dir_offset:\n');e=resolver.index('resolved_record:\n',a);resolver=resolver[:a]+resolver[e:]
 a=resolver.index('step_table:\n');e=resolver.index('opened:\n',a);resolver=resolver[:a]+'step_table:\n .word opened,verified,header_read,bca_bad,record_read\n'+resolver[e:]
 resolver=once(resolver,' cmp #13',' cmp #5')
 a=resolver.index(' lda LL_MODE\n bne @lex_root',resolver.index('opened:\n'));e=resolver.index('@shape:\n',a)
 resolver=resolver[:a]+''' lda BC_IO+31
 cmp #1
 beq @base
 cmp #LL_ROOT_FLAGS
 bne @unsupported
 lda BC_IO+98
 cmp #LL_LEX_ABI
 beq @shape
@unsupported:jsr cancel
 jmp miss
@base:lda BC_IO+98
 jne bca_corrupt
'''+resolver[e:]
 a=resolver.index(' lda LL_MODE\n bne @records');e=resolver.index('record_offset:\n',a)
 resolver=resolver[:a]+''' lda #5
 sta LL_STATE
 jmp bca_pending
'''+resolver[e:]
 a=resolver.index(' lda LL_MODE\n jne resolved_record',resolver.index('record_read:\n'));e=resolver.index('page_offset:\n',a)
 resolver=resolver[:a]+' jmp resolved_record\n'+resolver[e:]
 resolver=once(resolver,' lda BC_IO+2\n and #LL_LEX_COMPLETE\n jeq @miss',' lda BC_IO+3\n cmp #5\n jne bca_corrupt\n lda BC_IO+69\n cmp $9096+1+GSEM_LANG\n jne bca_corrupt\n lda BC_IO+2\n and #LL_LEX_COMPLETE\n jeq receipt')
 resolver=once(resolver,'.include "fold/source.inc"','.include "fold/source.inc"\n.include "render/geos/semantic.inc"')
 resolver=once(resolver,' lda BC_IO+2\n and #LL_LEX_COMPLETE\n jeq receipt',''' ldx #3
 ldy #22
 jsr source_sum
 ldx #6
 ldy #19
 jsr source_sum
 EQ LX_BODY,$9096+1+GSEM_BODY,3
 EQ LX_END,$9096+1+GSEM_END,3
 lda BC_IO+2
 and #LL_LEX_COMPLETE
 jeq receipt''')
 # Every candidate record has already passed actual full-page CRC, CR CRC,
 # ticket, source59, AUTH13 and exact START. NIL receipt carries that CR itself.
 resolver += '''
receipt:
 lda LL_ROOT+31
 cmp #1
 jne @miss_root
 ldy #3
@nil:lda BC_IO+47,y
 cmp #$FF
 jne bca_corrupt
 dey
 bpl @nil
 lda BC_IO+51
 ora BC_IO+52
 ora BC_IO+53
 jne bca_corrupt
 CP BC_IO,LX_PACKET,96
 jsr cancel
 CP LX_AUTH,LX+94,13
 CP LX_READER+27,LX+32,59
 lda #0
 sta LX_STATE
 sta LX_READY
 lda #4
 clc
 rts
@miss_root:jsr cancel
 jmp miss
'''
 # cancel owns this lease; descriptor/reader contents remain for receipt copy.
 resolver=once(resolver,'cancel_clear:\n lda #0','cancel_clear:\n lda se_bc_flags\n and #($FF-BC_ACTIVE)\n sta se_bc_flags\n lda #0')
 link('resolver',[('entry',resolver,[]),*[(n,arena[n],['BCA_READONLY_OPEN=1'])for n in ('core','open','page')]],addr='$A000')
 # Producer C47 owns the BC_ACTIVE reader while any child page operation runs.
 worker=(ROOT/'src/cache/lexical-probe/worker.s').read_text()
 worker=once(worker,'entry:\n',' jmp entry\noriginal_entry:\n')
 worker=once(worker,' cmp #4\n jeq reopen\n','')
 worker=once(worker,' cmp #BC_ARMED\n jne changed\n lda se_bc_count\n jne changed\n CP LX_AUTH',' cmp #(BC_ARMED|BC_ACTIVE)\n jne changed\n lda se_bc_count\n jne changed\n CP LX_AUTH')
 worker=once(worker,'@clear:lda #0\n sta LX_STATE','@clear:lda se_bc_flags\n and #($FF-BC_ACTIVE)\n sta se_bc_flags\n lda #0\n sta LX_STATE')
 worker+='''
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 bne @invoke
 lda se_bc_flags
 and #BC_ACTIVE
 jne busy
 lda #0
@invoke:
 sta $9096+27
 jsr original_entry
 bcs auto_error
 lda LX_LIVE
 beq :+
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
:
 lda $9096+27
 cmp #1
 bne auto_handoff
 lda LX_READY
 jeq pending
auto_handoff:
 lda #45
 sta $9135
 lda #1
 sta $9136
 clc
 rts
auto_error:
 sta $9096+26
 jmp auto_handoff
'''
 link('producer',[('worker',worker,[]),('lexer',lexer,['SE_SM_CODE_ONLY=1']),('state',lexer,['SE_SM_STATE_ONLY=1'])],segs=('LX_CODE','SM_LEXER','SM_STATE'))
 page=(ROOT/'src/cache/lexical-probe/page.s').read_text();page=once(page,' cmp #BC_ARMED',' cmp #(BC_ARMED|BC_ACTIVE)')
 link('roles',[('entry',page,[]),('core',arena['core'],[]),('page',arena['page'],[])],addr='$A000')
 # Writer-only C49 removes the unused resolver operation/state branch. Its COW
 # VALID-last algorithm and verification remain the released implementation.
 writer=(ROOT/'src/cache/lexical-link-probe/entry.s').read_text()
 writer=once(writer,'entry:\n',' jmp entry\noriginal_entry:\n');writer=once(writer,' cmp #3\n jeq resolve\n','')
 writer=once(writer,'.include "cache/lexical-link-probe/guard.inc"',guard)
 a=writer.index('resolve:\n');e=writer.index('start:\n',a);writer=writer[:a]+writer[e:]
 writer=once(writer,' lda LL_MODE\n bne source_matched\n','')
 a=writer.index(' lda LL_MODE\n bne @lex_root',writer.index('opened:\n'));e=writer.index('@shape:\n',a)
 writer=writer[:a]+''' lda BC_IO+98
 jne bca_bad
 lda BC_IO+31
 cmp #1
 jne bca_bad
'''+writer[e:]
 writer=once(writer,' lda LL_MODE\n bne @records\n','')
 writer=once(writer,'@records:lda #5\n sta LL_STATE\n jmp bca_pending\n','')
 writer=once(writer,' lda LL_MODE\n jne resolved_record\n','')
 a=writer.index('resolved_record:\n');writer=writer[:a]
 writer=once(writer,'cancel_clear:\n lda #0','cancel_clear:\n lda se_bc_flags\n and #($FF-BC_ACTIVE)\n sta se_bc_flags\n lda #0')
 writer+='''
entry:
 jsr bca_owner
 jcs link_return
 lda se_overlay_frame
 bne @invoke
 lda se_bc_flags
 and #BC_ACTIVE
 jne bca_stale
@invoke:
 jsr original_entry
 bcs auto_error
 lda LX_LIVE
 beq :+
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
:
 cmp #1
 beq auto_pending
 lda #45
 sta $9135
auto_pending:
 lda #1
 sta $9136
 clc
 rts
auto_error:
 sta $9096+26
 lda #45
 sta $9135
 jmp auto_pending
'''
 # Preserve the returned status across checking live/arming ACTIVE.
 writer=once(writer,' jsr original_entry\n bcs auto_error\n lda LX_LIVE',' jsr original_entry\n bcs auto_error\n pha\n lda LX_LIVE')
 writer=once(writer,':\n cmp #1\n beq auto_pending',':\n pla\n cmp #1\n beq auto_pending')
 link('writer',[('entry',writer,[]),*[(n,arena[n],['BCA_READONLY_OPEN=1'])for n in ('core','open','page')]])
 gateway=(D/'automatic-gateway.s').read_text();link('gateway',[('gateway',gateway,[])])
 # Preserve source-inline reuse under lexical proof kind81. This is the exact
 # independently qualified mixed milestone's two-byte kind mask.
 sources=[]
 for n in ('source-entry','source-seed','query','source','records','source-core','source-page'):
  t=(tree/'src/cache/inline'/(n+'.s')).read_text()
  if n=='source-seed':t=once(t,' lda BCQP_CACHE+3\n cmp #1',' lda BCQP_CACHE+3\n and #$7F\n cmp #1')
  sources.append((n,t,['BCQ_EDITOR_ACTIVE=1','BCQ_SELECTOR_OWNS_OWNER=1']))
 link('inline',sources)
 # R19's existing strict flag mask ignores only the new explicitly private
 # attempted bit in addition to existing bit16. Reserved bit64 still refuses.
 raw=(base/'build/overlays/rangeio.seo').read_bytes()[36:]
 symbols=json.load(open(report))['symbols']
 # reports store symbol addresses as integers in this frozen format.
 flag=symbols['se_bc_flags']
 if isinstance(flag,dict):flag=flag['address']
 if isinstance(flag,str):flag=int(flag,0)
 needle=bytes((0xad,flag&255,flag>>8,0x49,0x21,0x29,0xef))
 assert raw.count(needle)==1,'exact R19 strict flag-mask witness'
 at=raw.index(needle)+6;b['rangeio']=raw[:at]+b'\x6f'+raw[at+1:]
 r['rangeio']=dict(bytes=len(raw),changed_operand=at,old=239,new=111,sha256=hashlib.sha256(b['rangeio']).hexdigest())
 assert (0xef^0x6f)==128 and 0x6f&64
 for flags in range(256):assert flags&0x6f==(flags&0xef)&~128
 # A real fresh baseline commit starts a new attempt epoch. No caller clears
 # the latch merely to retry a failed lexical build. Existing H_INIT already
 # writes the whole flags byte; R33 success additionally clears private128.
 raw=(base/'build/overlays/fold.seo').read_bytes()[36:]
 needle=bytes((0xad,flag&255,flag>>8,0x29,0xf5,0x09,1,0x8d,flag&255,flag>>8))
 assert raw.count(needle)==1,'exact R33 successful baseline flag witness'
 at=raw.index(needle)+4;b['arena-writer']=raw[:at]+b'\x75'+raw[at+1:]
 r['arena-writer']=dict(bytes=len(raw),changed_operand=at,old=245,new=117,sha256=hashlib.sha256(b['arena-writer']).hexdigest())
 (out/'budget.json').write_text(json.dumps(r,indent=2)+'\n');return b,l,r
