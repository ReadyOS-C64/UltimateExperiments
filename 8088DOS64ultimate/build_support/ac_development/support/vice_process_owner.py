"""Fail-closed OS proof that a connected monitor socket belongs to a live child.

macOS/Unix lsof is required. Localhost alone and a live unrelated PID are not
ownership. No monitor bytes are sent by this module.
"""
import ipaddress,shutil,subprocess,time
from pathlib import Path

def lsof_tool():
    found=shutil.which('lsof')
    if found:return str(Path(found).resolve())
    if Path('/usr/sbin/lsof').is_file():return '/usr/sbin/lsof'
    raise ValueError('lsof is required to prove VICE monitor ownership')

def accepted_owner(output,pid,server,client):
    """Parse -F pfnT records and match the accepted ESTABLISHED four-tuple."""
    expected=f'{server[0]}:{server[1]}->{client[0]}:{client[1]}'
    current_pid=None;record={};matches=0
    def matches_record():
        return current_pid==pid and record.get('n')==expected and record.get('state')=='ESTABLISHED' and record.get('f','').rstrip('urw').isdigit()
    for line in output.splitlines()+['fEND']:
        if not line:continue
        tag,value=line[0],line[1:]
        if tag in ('p','f'):
            if matches_record():matches+=1
            record={}
            if tag=='p':
                if not value.isdigit():raise ValueError('Invalid lsof PID')
                current_pid=int(value)
            else:record['f']=value
        elif tag=='n':record['n']=value
        elif tag=='T' and value.startswith('ST='):record['state']=value[3:]
    return matches==1

class ChildMonitorOwner:
    def __init__(self,child,sock,deadline,tool=None):
        self.child=child;self.sock=sock;self.deadline=deadline;self.tool=tool or lsof_tool();self.proof=None
        self.client=self._endpoint(sock.getsockname());self.server=self._endpoint(sock.getpeername())
        if self.client==self.server:raise ValueError('Invalid monitor four-tuple')
    @staticmethod
    def _endpoint(value):
        if len(value)!=2 or str(ipaddress.ip_address(value[0]))!='127.0.0.1' or not 0<int(value[1])<65536:raise ValueError('Only IPv4 localhost monitor endpoints are allowed')
        return ('127.0.0.1',int(value[1]))
    def require(self,wait=False):
        stop=min(self.deadline,time.monotonic()+(2.0 if wait else .5))
        while True:
            if self.child.poll() is not None:raise ValueError('Fresh VICE child is no longer alive')
            if self._endpoint(self.sock.getsockname())!=self.client or self._endpoint(self.sock.getpeername())!=self.server:raise ValueError('Monitor connection endpoints changed')
            remaining=stop-time.monotonic()
            if remaining<=0:raise ValueError('Cannot prove accepted VICE monitor ownership before deadline')
            result=subprocess.run([self.tool,'-nP','-a','-p',str(self.child.pid),'-iTCP','-F','pfnT'],capture_output=True,text=True,timeout=min(1.0,remaining),check=False)
            if result.returncode not in (0,1):raise ValueError('lsof ownership inspection failed')
            if self.child.poll() is not None:raise ValueError('Fresh VICE child exited during ownership inspection')
            if result.returncode==0 and accepted_owner(result.stdout,self.child.pid,self.server,self.client):
                self.proof={'method':'lsof accepted ESTABLISHED socket','child_pid':self.child.pid,'server':list(self.server),'client':list(self.client),'lsof_path':self.tool};return self.proof
            if not wait:raise ValueError('Connected monitor is not owned by the fresh VICE child')
            time.sleep(min(.025,max(0,stop-time.monotonic())))

class OwnedBinaryMonitor:
    """Check accepted socket/PID ownership before every binary monitor command."""
    def __init__(self,sock,owner):
        from vice_monitor import BinaryMonitor
        class Checked(BinaryMonitor):
            def call(inner,typ,body=b''):
                owner.require()
                return super(Checked,inner).call(typ,body)
        owner.require(wait=True)
        self.monitor=Checked(sock);self.owner=owner
    def __getattr__(self,name):return getattr(self.monitor,name)
