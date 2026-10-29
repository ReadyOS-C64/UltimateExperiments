"""Actual root pending/high24/nowrap stylewindow packets, independentpixels."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json
import test_geos_style_window_candidate as candidate
import test_geos_inline161_candidate as existing
ROOT=candidate.ROOT

def run(out):
 candidate.certificate.D=ROOT/'src/render/geos/style-window-candidate';fixture=candidate.certificate.install(out,candidate.BASE);target=out/'gate';target.mkdir()
 text=inspect.getsource(existing.public)
 text=text.replace('def check(data,tag,pan=1,nowrap=True,caret=0):','def check(data,tag,pan=1,nowrap=True,caret=0,top=0,pending=False):')
 old='  f.source(data);f.command(99);f.position(caret)'
 new="""  f.command(96);f.source(data);f.position(caret)
  if pending:
   value=geos.native_text('Q')[0];f.key(value);data=data[:caret]+bytes([value])+data[caret:];caret+=1
   assert f.get('se_hot_pending',1),'realpending edit didnotremainpending'
  f.command(99)
  if pending:assert f.get('se_hot_pending',1),'modecommand flushedpending'"""
 assert text.count(old)==1;text=text.replace(old,new).replace("f.put('se_v_top',0)","f.put('se_v_top',top)")
 a=text.index('  check(b\'.\'*200');b=text.index('  result=dict(',a)
 text=text[:a]+"""  exact=b'**'+b'.'*48+b'**'+b'.'*76
  check(exact+b'\\rTail.','exact320-packet128-cr',0,False)
  check(exact,'exact320-packet128-eof',0,False)
  prefix=b'x'*65530+b'\\r'
  data=prefix+geos.native_text('# **'+('Wim. '*60)+'end**\\rTail.')
  check(data,'high24-pending-softwrap',0,False,65540,65531,True)
  check(data,'high24-pan399',399,True,65540,65531)
  check(data,'high24-pan999-certificate-miss',999,True,65540,65531)
"""+text[b:]
 ns=dict(existing.__dict__);exec(text,ns);r=ns['public'](target,fixture);r['scope']+=' Addedrealpending source packet seam at64KiB; manualpan399/999 withindependentnegativeleftoracle andcanonicalglobalanchors.';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 out=ROOT/'build/geos-style-window-boundaries'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out);print({'status':r['status'],'frames':len(r['frames'])},flush=True)
