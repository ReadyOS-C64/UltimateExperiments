"""Independent PETSCII word/search/goto oracle through the actual editor."""
import hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from run_vice import native_screen_text
f=EditorFixture();result=ROOT/'build/search-test-result.json';result.unlink(missing_ok=True)
def fold(data):return bytes(c&0x7F if 0xC1<=c<=0xDA else c&0x5F if 0x61<=c<=0x7A else c for c in data)
def word(c):return c==0x5F or 48<=c<=57 or 65<=c<=90 or 97<=c<=122 or 193<=c<=218
def expected_word(data,p,right):
 if right:
  while p<len(data) and word(data[p]):p+=1
  while p<len(data) and not word(data[p]):p+=1
 else:
  while p and not word(data[p-1]):p-=1
  while p and word(data[p-1]):p-=1
 return p
def search(data,pattern,p,insensitive=False,next=False):
 start=min(p+1,len(data)) if next else p
 hay,needle=(fold(data),fold(pattern)) if insensitive else (data,pattern)
 found=hay.find(needle,start)
 return found if found>=0 else hay.find(needle,0,min(len(hay),start+len(needle)-1))
def pattern(value,insensitive=False):
 f.m.load(f.s['se_s_pattern'],value);f.put('se_s_length',len(value),1);f.put('se_s_insensitive',int(insensitive),1)
def run_find(data,value,p,insensitive=False,next=False):
 f.position(p);pattern(value,insensitive);target=search(data,value,p,insensitive,next)
 f.command(46 if next else 45,error=0x7E if target<0 else 0,render=target>=0)
 assert f.get('se_hot_caret')==(p if target<0 else target),(p,value,target,f.get('se_hot_caret'))
try:
 rng=random.Random(0x53454152)
 data=bytes([0xC1,0x42,0x5F,0x39,32,0xA1,13,0,0xFF])+b'ONE--TWO\rTHREE  '+bytes(range(256))*2
 f.source(data)
 for _ in range(150):
  p=rng.randrange(len(data)+1);right=bool(rng.randrange(2));f.position(p);f.command(43 if right else 42,render=True)
  assert f.get('se_hot_caret')==expected_word(data,p,right),(p,right,f.get('se_hot_caret'))
 assert f.document()==data
 print('150 word movements across native cases,graphics,controls and EOF pass.',flush=True)
 # Source positions, all native byte values, exact/insensitive case and wrap.
 data=bytes(range(256))*2+b'ABABABABAC'+bytes([0xC1,0xC2,0xC3])+b'ABC'+b'Z'*30
 f.source(data)
 for _ in range(100):
  p=rng.randrange(len(data)+1);a=rng.randrange(len(data));value=data[a:a+rng.randrange(1,12)]
  run_find(data,value,p,bool(rng.randrange(2)),bool(rng.randrange(2)))
 for value in [b'ABABAC',b'ZZZZZZZZZZZZZZZZZZZZZZZZZZ',bytes([0xFE,0xFD]),b'ABC',bytes([0xC1,0xC2,0xC3])]:
  for p in [0,127,len(data)//2,len(data)]:
   for insensitive in [False,True]:run_find(data,value,p,insensitive)
 # The wrapped match can begin before origin and finish after it; never match
 # suffix+prefix across EOF. KMP must retain overlap state across128-work slices.
 for data,value,p in [(b'ABCABC',b'ABC',2),(b'AB',b'BA',1),(b'A'*600+b'B',b'A'*25+b'B',130),(b'AAAA',b'AA',1),(b'',b'X',0)]:
  f.source(data);run_find(data,value,p);run_find(data,value,p,next=True)
 print('Literal/KMP overlap,case,128-step boundaries,wrap and not-found pass.',flush=True)
 # Typed literal arguments retain native case; keyword case folds only letters.
 data=b'ABC'+bytes([0xC1,0xC2,0xC3])+b'\rLAST';f.source(data)
 f.typed(b'FIND '+bytes([0xC1,0xC2,0xC3]));assert f.get('se_hot_caret')==3
 assert f.read(f.s['se_s_pattern'],3)==bytes([0xC1,0xC2,0xC3])
 f.typed(b'FINDI ABC');assert f.get('se_hot_caret')==3
 f.command(34);f.key(6);assert f.get('se_e_ui',1)==2 and f.read(f.s['se_e_text'],5)==b'FIND '
 for c in b'ABC':f.key(c)
 f.key(13);assert f.get('se_hot_caret')==0
 f.key(0x85);f.key(0x4E);f.key(0x57);assert f.get('se_hot_caret')==7 #both native cases form one word, then CR before LAST
 # Goto uses one-based CR logical lines, not soft-wrap rows; decimal overflow
 # and absent lines never move caret or mutate the source.
 data=b'A'*83+b'\r\r'+b'B'*200+b'\rTAIL\r';f.source(data)
 starts=[0]+[i+1 for i,v in enumerate(data) if v==13]
 for line,p in enumerate(starts,1):
  f.typed(b'GOTO '+str(line).encode());assert f.get('se_hot_caret')==p,(line,p,f.get('se_hot_caret'))
 for text,error in [(b'GOTO 0',0x7C),(b'GOTO -1',0x7C),(b'GOTO 16777216',0x7C),(b'GOTO 1X',0x7C),(b'GOTO 6',0x7D)]:
  p=f.get('se_hot_caret');f.typed(text,error);assert f.get('se_hot_caret')==p
  if f.get('se_e_ui',1):f.key(3)
 assert f.document()==data
 # Goto after pending newline and undo must use the updated logical line index.
 f.command(34);f.key(13);f.typed(b'GOTO 2');assert f.get('se_hot_caret')==1
 assert f.document()==b'\r'+data
 f.command(16);f.typed(b'GOTO 2');assert f.get('se_hot_caret')==starts[1] and f.document()==data
 print('Typed native-case queries,prompt/menu routes,goto and invalid arguments pass.',flush=True)
 # Sparse checkpoint reuse and24-bit line numbers/byte positions.
 data=b'\r'*65553+b'ABABAC';f.source(data)
 f.command(35)
 for line in [65554,40001,8193,1,65536]:
  f.put('se_g_line',line);f.command(44,render=True);assert f.get('se_hot_caret')==line-1
 run_find(data,b'ABABAC',65000);assert f.get('se_hot_caret')==65553
 assert f.document()==data
 # Real event-loop cancellation; a failed evicted C9 reload releases its lease.
 f.source(b'Q'*70000);pattern(b'NO');f.call('se_editor_command',45)
 assert f.get('se_s_owned',1)==1
 f.m.write(f.s['se_input_chars'],3);f.put('se_input_head',1,1);f.put('se_input_tail',0,1);f.call('se_editor_service');f.settle()
 assert f.get('se_hot_caret')==0 and f.get('se_key_sequence',2)==1
 f.call('se_editor_command',45);f.call('se_editor_service');f.call('se_history_call',10)
 index=next(i for i in range(12) if f.m.read(f.s['se_overlay_ids']+i)==9 and f.m.read(f.s['image_slot']+i)==1)
 from overlays import HEADER
 f.put('se_reu_logical',f.get('se_overlay_asset',1),1);f.put('se_reu_offset',index*4096+20,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x5000,2);f.m.write(0x5000,f.assets['search'][HEADER+20]^1);assert not f.call('se_reu_copy').p&1
 f.call('se_editor_service');f.settle(0x14);assert f.get('se_hot_caret')==0
 # A provider reset cannot let old search cancellation release a foreign lease.
 f.put('se_reu_logical',f.get('se_overlay_asset',1),1);f.put('se_reu_offset',index*4096+20,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x5000,2);f.m.write(0x5000,f.assets['search'][HEADER+20]);assert not f.call('se_reu_copy').p&1
 f.put('se_e_error',0,1);f.call('se_editor_command',45);assert f.get('se_s_owned',1)==1
 f.put('se_reu_banks',8,2)
 for n,a in [('se_reu_provider_init',0),('se_object_init',0),('se_doc_init',1)]:assert not f.call(n,a).p&1
 f.put('se_doc_source_length',0);assert not f.call('se_doc_adopt_original').p&1;assert not f.call('se_doc_read_acquire').p&1
 f.call('se_search_cancel');assert f.get('se_doc_read_locks',1)==1
 f.call('se_doc_read_release')
 assert f.read(0xC600,1024)==f.shim
 report=dict(status='passed',prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()},word_cases=150,random_search_cases=100,case_and_wrap_fixtures=True,typed_native_case=True,logical_goto=True,line_numbers_over_65535=True,cancel_and_reload_cleanup=True,foreign_epoch_lease_preserved=True,max_service_instructions=f.max_service,shim_bytes_verified=1024,limitations='CPU source40 commands;native screenshots and physical chords/normal timing separate.')
 result.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:f.close()
