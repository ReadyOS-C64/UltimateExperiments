"""Private local-status candidate: exact typing6 + warmcaret4 PAL profile."""
from pathlib import Path
import inspect
import test_grid_typing_candidate_vice as preparation
import test_source_grid_typing_profile_vice as profile
ROOT=profile.ROOT
original=profile.scenario
def scenario(e):
 n=original(e);data=profile.PLAIN;at=data.index(profile.timing.native.live.grid.native_text('having'))+2
 for mode in (1,2):
  n.mode_to(mode);n.typed('warmcaret_goto'+str(mode),'goto 2');n.send('warmcaret_column'+str(mode),b'\x1d'*(at-data.index(b'\r')-1));n.memory('warmcaret_start'+str(mode),'se_hot_caret',at,3)
  n.measure('m'+str(mode)+'-warm-right',data,mode,key=0x1d);n.measure('m'+str(mode)+'-warm-left',data,mode,key=0x9d)
 return n
if __name__=='__main__':
 profile.scenario=scenario
 source=inspect.getsource(preparation.main);needle="ROOT/'src/render/grid/typing-candidate/build.py'";assert source.count(needle)==1
 namespace=dict(preparation.__dict__);exec(compile(source.replace(needle,"ROOT/'src/render/grid/typing-candidate/build-local.py'"),str(Path(__file__))+':local-build', 'exec'),namespace);namespace['main']()
