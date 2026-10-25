"""Literal argument boundaries through actual F7 parser and search admission."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
result_path=ROOT/'build/search-arguments-result.json';result_path.unlink(missing_ok=True)
f=EditorFixture()
try:
 data=b'LEFT  RIGHT\r'+b'A'*26+b'\r'+bytes([0xC1])*25+b' NEXT NEXT'
 f.source(data)
 for text,expected,insensitive in [(b'FIND '+b'A'*26,12,0),(b'FINDI '+bytes([0xC1])*25,12,1),(b'FIND  ',4,0)]:
  f.command(34);f.typed(text);assert f.get('se_hot_caret')==expected,(text,f.get('se_hot_caret'),expected)
  assert f.get('se_s_length',1)==len(text)-(6 if insensitive else 5)
  assert f.get('se_s_insensitive',1)==insensitive
 f.command(34);f.typed(b'FIND NEXT');first=data.find(b'NEXT');assert f.get('se_hot_caret')==first
 f.typed(b'NEXT MATCH');assert f.get('se_hot_caret')==data.find(b'NEXT',first+1)
 old=f.read(f.s['se_s_pattern'],26);length=f.get('se_s_length',1)
 for text in [b'FIND ',b'FINDI ',b'GOTO ',b'GOTO +1']:
  p=f.get('se_hot_caret');f.typed(text,0x7C);assert f.get('se_hot_caret')==p
  assert f.read(f.s['se_s_pattern'],26)==old and f.get('se_s_length',1)==length
  f.key(3)
 for length in [0,27,255]:
  f.put('se_s_length',length,1);p=f.get('se_hot_caret');f.command(46,0x7C);assert f.get('se_hot_caret')==p
 assert f.document()==data and f.read(0xC600,1024)==f.shim
 result=dict(status='passed',prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()},literal_26_and_folded_25_byte_limits=True,literal_next_and_repeat_command_distinct=True,space_literal_preserved=True,empty_or_invalid_arguments_preserve_query_and_caret=True,invalid_raw_pattern_length_rejected=True,source_unchanged=True,shim_bytes_verified=1024)
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:f.close()
