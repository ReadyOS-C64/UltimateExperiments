"""Private bufferedproducer with actualreaderror poisoning and range-provenbranches."""
from pathlib import Path
import importlib.util,inspect,sys
D=Path(__file__).resolve().parent
RELEASED=D.parent/'geowrite-reflow-candidate'
sp=importlib.util.spec_from_file_location('releasedcurrent',RELEASED/'build-current.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def build(out,base=m.BASE,pixel=True):
 src=inspect.getsource(m.build)
 needle='read:jsr se_fs_read\n bcs :+\n jmp se_sc_scan\n: rts'
 hook='read:jsr se_fs_read\n bcc :+\n pha\n jsr se_sc_read_failed\n pla\n sec\n rts\n: jmp se_sc_scan'
 injection=' text='+repr('.import se_sc_read_failed\n')+'+text.replace('+repr(needle)+','+repr(hook)+')\n entry.write_text('
 src=src.replace(' entry.write_text(',injection)
 src=src.replace(' objs=[]\n for i,path'," for name in ('source-context.s','source-read.s'):(project/'src/fold'/name).write_text((BUFFER/name).read_text())\n objs=[]\n for i,path")
 ns=dict(m.__dict__,BUFFER=D);exec(compile(src,str(__file__)+':private-read-error-hook-and-branch-ranges','exec'),ns)
 return ns['build'](out,base,D/'producer.s',pixel=pixel,dispatch=True)
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
