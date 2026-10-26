"""Private C25→C45→C21 admission; same sealed public oracles and faults."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Apply the released adaptive wrapper's exact, guarded recipe without executing
# its CLI, then replace only the registered private adapters/PC counters.
p=ROOT/'tests/test_cache_lexical_adaptive.py';text=p.read_text();assert text.endswith("exec(compile(s,str(p),'exec'),globals())\n")
exec(compile(text.rsplit('exec(compile(',1)[0],str(p),'exec'),globals())
s=s.replace("ROOT/'src/cache/lexical-adaptive-probe/build.py'","ROOT/'src/cache/lexical-admission-probe/build.py'")
s=s.replace("ROOT/'build/cache-lexical-adaptive'","ROOT/'build/cache-lexical-admission'")
old="('geoslex',binaries['gateway'],1,25)";assert s.count(old)==1
s=s.replace(old,"('geoslex',binaries['strict'],1,25),('lexgate',binaries['gateway'],1,45)")
old=",('line',binaries['fallback'],1,39)";assert s.count(old)==1;s=s.replace(old,'')
s=s.replace("request==25 and self.m.read(0x9135)==39","request==45 and self.m.read(0x9135)==25")
old="list(f.assets).index('geoslex')+1,list(f.assets).index('line')+1,ls['gateway']['cache_hit'],0,0,ls['fallback']['se_sl_feed']";assert s.count(old)==1
s=s.replace(old,"list(f.assets).index('lexgate')+1,list(f.assets).index('geoslex')+1,ls['gateway']['cache_hit'],0,0,ls['strict']['se_sl_feed']")
s=s.replace("f.m.read(0x9135)==25 and f.m.read(0x9096)","f.m.read(0x9135)==45 and f.m.read(0x9096)")
# Add one ordinary long root1 cost control; it must never visit C45.
s=s.replace("   if caps and len(data)>100:","   if caps and len(data)>100 and tag!='unlinked-long-root1':")
s=s.replace("  r=super().call(name,a)","  if name=='se_editor_service'and request==45:self.gateway_calls=getattr(self,'gateway_calls',0)+1\n  r=super().call(name,a)")
s=s.replace('f.query_trace=[]','f.query_trace=[];f.gateway_calls=0')
s=s.replace('   frame=dict(query_begins=query_begins,','   frame=dict(gateway_service_calls=f.gateway_calls,query_begins=query_begins,')
old="  result=dict(status='passed-parent'"
assert s.count(old)==1
s=s.replace(old,"""  assert frames[-1]['gateway_service_calls']==0 and frames[-1]['loads']==frames[-1]['baseline_loads']
  data=geos.native_text('Intro\\r:::basic\\r10 PRINT "Hi":REM ')+geos.native_text('x')*980+geos.native_text('\\r:::\\rTail.')
  for x in(f,g):x.source(data);x.command(99);x.render()
  check('unlinked-long-root1',False)
  assert frames[-1]['gateway_service_calls']==0 and frames[-1]['loads']==frames[-1]['baseline_loads']
  assert all(q[2]==1 for q in frames[-1]['query_begins']if q[0]==37)
"""+old)
exec(compile(s,str(ROOT/'tests/test_cache_lexical_editor.py'),'exec'),globals())
