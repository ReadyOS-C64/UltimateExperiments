"""Private adaptive parent-window qualification; released verifier stays immutable.

The sealed parent verifier retains all ten source/pixel/REU/error cases. This
wrapper changes only the private builder and adds C37/C21 matched proof modules.
It does not transform the source, model, expectations, or measurement seam.
"""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'tests/test_cache_lexical_editor.py';source=p.read_bytes()
assert hashlib.sha256(source).hexdigest()=='2c3e3910761328364cc395d556e5ae0c2295c816eb80f5078e0de7cf4360c24a'
s=source.decode()
old="ROOT/'src/cache/lexical-editor-probe/build.py'";assert s.count(old)==1
s=s.replace(old,"ROOT/'src/cache/lexical-adaptive-probe/build.py'")
old="('inln',binaries['query'],1,35)";assert s.count(old)==1
s=s.replace(old,old+",('page',binaries['forward'],1,37),('geospage',binaries['page'],1,21)")
s=s.replace("ROOT/'build/cache-lexical-editor'","ROOT/'build/cache-lexical-adaptive'")
old="  r=super().call(name,a)"
assert s.count(old)==1
s=s.replace(old,"""  if name=='se_editor_service'and request in(35,37):
   op=self.m.read(0x9136)
   if request==37 and op==0:
    fault=getattr(self,'proof_fault',None)
    if fault:
     import binascii
     cert=bytearray(self.read(0x8b40+29,85));cert[75]^=0x80 if fault=='crc' else 0x40
     if fault=='kind':cert[83:85]=binascii.crc_hqx(bytes(reversed(cert[:83])),65535).to_bytes(2,'little')
     self.m.load(0x8b40+29,cert);self.proof_fault=None;self.proof_fault_injected=True
   self.query_trace=getattr(self,'query_trace',[])+[(request,op,self.m.read(0x8ba8))]
  r=super().call(name,a)""")
s=s.replace('   f.window_trace=[]','   f.window_trace=[];f.query_trace=[]')
old="   frame=dict(tag=tag,render_instructions=used"
assert s.count(old)==1
s=s.replace(old,"""   query_begins=[x for x in f.query_trace if x[1]==0]
   if caps and len(data)>100:
    assert any(x[0]==37 for x in query_begins),(tag,'actualforwardBEGIN',query_begins)
    assert any(x[0]==37 and x[2]==0x81 for x in query_begins),(tag,'authenticatedlexcap-forward',query_begins)
   frame=dict(query_begins=query_begins,tag=tag,render_instructions=used""")
old="  for name,caps in [('plain',0),('markdown',1)]:"
assert s.count(old)==1
s=s.replace(old,"""  # Fault only actual completed certificate before the first real C37 BEGIN.
  # One bad CRC and one CRC-valid unknown kind must fall back through C35.
  for fault in ('crc','kind'):
   f.proof_fault=fault;f.proof_fault_injected=False
   check('proof-'+fault+'-recovery')
   assert f.proof_fault_injected and sum(q[0]==35 for q in frames[-1]['query_begins'])>=2
"""+old)
s=s.replace("PrivatestrictC35 acceptsflags1/5 withlexABI0/1 andrealCRclassification; noPAGE_REUSE/CP79/outgoingcert claim.","Private optimizedC35/C37 preservePAGE_REUSE andforward;CRC85-coveredkind1/base or81/lex;actualC21capturemaskedlowkind;nofakeCP79.")
exec(compile(s,str(p),'exec'),globals())
