"""Complete resident binding changes cannot hide behind stable call/frame pairs."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from bindings import DOMAIN,binding_digest,link_symbols,seal,verify
from overlays import wrap
result_path=ROOT/'build/bindings-test-result.json';result_path.unlink(missing_ok=True)
report=json.loads((ROOT/'build/overlay-probe-report.json').read_text());s=report['symbols']
image=(ROOT/'build/overlay-probe.prg').read_bytes();pairs=link_symbols(ROOT/'build/overlay-probe.lbl')
digest,at=binding_digest(image,pairs)
normalized=image[:at]+bytes(16)+image[at+16:]
independent=hashlib.sha256(DOMAIN+normalized+b'\0'+json.dumps(pairs,separators=(',',':'),ensure_ascii=True).encode('ascii')).digest()[:16]
assert digest==independent==bytes.fromhex(report['resident_binding']['digest'])
with tempfile.TemporaryDirectory(prefix='supereditor-bindings-') as work:
 work=Path(work);prg=work/'resident.prg';labels=work/'resident.lbl'
 prg.write_bytes(image);original_labels=(ROOT/'build/overlay-probe.lbl').read_text();labels.write_text(original_labels)
 first=seal(prg,labels);again=seal(prg,labels);assert first==again and prg.read_bytes()==image
 # Private/public RAM labels after the pair can move without changing any
 # resident instruction. They are still part of this complete binding seal.
 target='se_last_key';old=s[target];changed=[]
 for line in original_labels.splitlines():
  if line.endswith(' .'+target):line=f'al {old+1:06X} .{target}'
  changed.append(line)
 labels.write_text('\n'.join(changed)+'\n')
 try:verify(prg,labels);raise AssertionError('stale link binding accepted')
 except ValueError:pass
 foreign=seal(prg,labels);new_digest=bytes.fromhex(foreign['digest'])
 assert new_digest!=digest
 altered=dict(link_symbols(labels))
 assert altered['se_overlay_call']==s['se_overlay_call'] and altered['se_overlay_frame']==s['se_overlay_frame']
 payload=(ROOT/'build/overlays/probe-rtwo.bin').read_bytes()
 try:wrap(payload,0,2,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=new_digest);raise AssertionError('old compiled prefix accepted')
 except AssertionError as exc:
  assert 'another resident build' in str(exc)
 # Modifying a resident instruction, preserving every symbol, also invalidates.
 labels.write_text(original_labels);prg.write_bytes(image)
 changed=bytearray(image);entry=s['se_entry']-0x801+2;changed[entry]^=1;prg.write_bytes(changed)
 try:verify(prg,labels);raise AssertionError('stale image seal accepted')
 except ValueError:pass
 assert seal(prg,labels)['digest']!=digest
 # Reordered/repeated link lines do not cause needless nondeterminism.
 prg.write_bytes(image);labels.write_text('\n'.join(reversed(original_labels.splitlines()))+'\n'+original_labels)
 assert seal(prg,labels)['digest']==digest.hex()
result=dict(status='passed',resident_sha256=report['sha256'],abi=2,binding_digest=digest.hex(),digest_bytes=16,
 complete_image_and_link_symbols=True,same_call_frame_with_moved_ram_rejected=True,
 stale_compiled_payload_rejected=True,changed_resident_code_rejected=True,idempotent_sealing=True)
result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
