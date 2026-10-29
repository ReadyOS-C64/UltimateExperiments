"""Original native29 pixel/REU/ownership oracle for local-status variant."""
from pathlib import Path
import inspect,sys
import test_grid_typing_gallery_vice as original
if __name__=='__main__':
 source=inspect.getsource(original.freeze)
 for old,new in [('2414','4096'),('e9b657cf42f38ef57f4a9bad47179c084830cc97ad608839926385077bd968cf','41bd9353a11148637b6e2a9faad2c5034c65ce4549b5a8873ce83b1d7d95ade4'),('3543','3586'),('0ad94e310eb3f5034eb4126eb14c138d095ca49ac516789874198bd7c4262afc','db40a9426a3e6d53f8ea9768418aaf59158d46f5fd6a646c7f7120e56db17b5c')]:
  assert source.count(old)==1;source=source.replace(old,new)
 source=source.replace("'-grid-typing-gallery-native'","'-grid-typing-local-gallery-native'")
 namespace=dict(original.__dict__);exec(compile(source,str(Path(__file__))+':exact-variant-freeze', 'exec'),namespace);original.freeze=namespace['freeze'];original.main()
