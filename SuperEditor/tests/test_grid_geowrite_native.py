"""Finalprivatecurrent203233 capsule: same8longcases plus4mixedfallbacks,8100/8200."""
import inspect,json
import test_grid_long_transaction_vice as long


old_scenario=long.scenario
def scenario(e):
 n=old_scenario(e);raw=long.timing.native.live.grid.fixture();n.open('mixed_open',b'DIVERSE')
 for mode in (1,2):
  group='mixed-m'+str(mode);n.mode_to(mode);n.typed(group+'_top','top');data=raw
  for i,key in enumerate((81,20)):
   data=bytes((81,))+raw if i==0 else raw
   ident=group+'-edit'+str(i);n.measure(ident,data,mode,key=key,category='mixed-source-wholeplan-fallback');n.measurements[-1]['group']=group
 return n
long.scenario=scenario
if __name__=='__main__':
 src=inspect.getsource(long.main).replace("'long-prose-pal'","'geowrite-final-pal'")
 ns=dict(long.__dict__);exec(compile(src,__file__+':same-native-guards','exec'),ns);ns['main']()
