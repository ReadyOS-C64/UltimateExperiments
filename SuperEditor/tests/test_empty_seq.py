"""Isolated empty-SEQ investigation: raw D81 oracle, emitted preflight and
optional actual KERNAL/.NET VICE run (requires root's exclusive window).
"""
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROBE=ROOT/'probes/empty_seq'
sys.path.insert(0,str(ROOT/'tools'))
from fileio_fixture import FileIOFixture
from peddle import Machine

def sector(image,t,s):
    assert 1<=t<=80 and 0<=s<40,(t,s)
    at=((t-1)*40+s)*256;return image[at:at+256]
def files(image):
    t,s=40,3;out={};seen=set()
    while t:
        assert (t,s) not in seen;seen.add((t,s));b=sector(image,t,s)
        for i in range(8):
            e=b[i*32:i*32+32]
            if not e[2]&7:continue
            name=e[5:21].rstrip(b'\xa0');ft,fs=e[3:5];data=bytearray();chain=[];visited=set()
            while ft:
                assert (ft,fs) not in visited;visited.add((ft,fs));q=sector(image,ft,fs)
                chain.append((ft,fs,q))
                if q[0]:data.extend(q[2:])
                else:
                    assert q[1]>=1
                    data.extend(q[2:q[1]+1]) # last-used index1 encodes zero payload
                ft,fs=q[:2]
            out[name]=dict(data=bytes(data),chain=chain,type=e[2],entry=bytes(e))
        t,s=b[:2]
    return out
def labels():
    return {n.lstrip('.'):int(v,16) for _,v,n in
            (line.split() for line in (PROBE/'build/empty-seq.lbl').read_text().splitlines())}

class Fixture(FileIOFixture):
    def __init__(self):
        self.s=labels();self.m=Machine();self.m.load(0x801,(PROBE/'build/empty-seq.prg').read_bytes()[2:])
        self.fs={};self.channels={};self.trace=[];self.selected_in=self.selected_out=None
        self.st=0;self.dos=b'00, OK,00,00\r';self.directory=b'';self.inject={};self.blocks={}
        self.shim=bytes((i*43+17)&255 for i in range(1024));self.m.load(0xC600,self.shim)
        self.call('se_io_init')
    def call(self,name,a=0,error=None):
        # Base fixture requiresA0 for success; these continuation entries return
        # A2 pending. Capture and verify its actual value separately below.
        if name in ('empty_begin','empty_step'):
            old=self.s.get('_probe_return')
            m=self.m
            for k,v in [('pc',self.s[name]),('a',a),('x',0),('y',0),('sp',0xFD),('p',0x24)]:
                getattr(m.lib,'zeropage_peddle_set_'+k)(m.handle,v)
            m.write(0x1FE,0xFE);m.write(0x1FF,0x02)
            for _ in range(200000):
                if m.regs().pc==0x02FF:break
                if m.regs().pc>=0xFF80:self.rom()
                else:m.lib.zeropage_peddle_step_instruction(m.handle)
            else:raise AssertionError(name)
            r=m.regs()
            assert bool(r.p&1)==(error is not None),(name,r.a,error)
            if error is not None:assert r.a==error
            else:assert r.a in (0,2)
            assert self.read(0xC600,1024)==self.shim
            return r.a
        return super().call(name,a,error)
    def rom(self):
        if self.m.regs().pc==0xFFC0 and self.filename==b'#':
            saved=self.filename;self.filename=b'0:__RAW,S,R';self.fs[b'__RAW']=bytes(256)
            super().rom();self.filename=saved
        else:super().rom()
    def command(self,cmd):
        if cmd.startswith(b'U1:'):
            ch,drive,t,s=map(int,cmd[3:].split());assert (ch,drive)==(3,0)
            self.channels[7]=dict(data=self.blocks[(t,s)],pos=0)
            self.dos=b'00, OK,00,00\r'
        else:super().command(cmd)
def offline():
    old=ROOT/'agentsworking/evidence/M4/20261024T182931526521Z-fileio-native'
    records=files((old/'working.d81').read_bytes());empty=records[b'EMPTY']
    assert empty['data']==b'' and empty['chain'][0][2][:2]==b'\0\1'
    assert (old/'empty.seq').read_bytes()==empty['chain'][0][2][2:]
    # Independent reproduction of3.10's sequential-read index arithmetic.
    q=empty['chain'][0][2];ptr=2;read=bytearray()
    while True:
        read.append(q[ptr])
        if ptr==q[1]:ptr=255
        ptr=(ptr+1)&255
        if ptr==0:break
    assert bytes(read)==(old/'empty.seq').read_bytes() and len(read)==254
    f=Fixture();cases=[]
    try:
        header=bytearray(256);header[:2]=b'\x28\x03'
        directory=bytearray(256);directory[:2]=b'\0\xff'
        entries=[(b'EMPTY',39,0,b'\0\1'),(b'NUL',39,1,b'\0\2\0'),
                 (b'FULL',39,2,b'\x27\x03')]
        for n,(name,t,s,prefix) in enumerate(entries):
            at=n*32;directory[at+2]=0x81;directory[at+3:at+5]=bytes([t,s])
            directory[at+5:at+21]=name.ljust(16,b'\xa0')
            f.blocks[(t,s)]=prefix.ljust(256,b'\xac')
        f.blocks[(40,0)]=bytes(header);f.blocks[(40,3)]=bytes(directory)
        for name,expected in [(b'EMPTY',1),(b'NUL',0),(b'FULL',0)]:
            f.name(name);assert f.call('empty_begin')==2
            steps=0
            while f.call('empty_step')==2:steps+=1;assert steps<40
            assert f.read('empty_result')[0]==expected and not f.channels
            cases.append(dict(name=name.decode(),empty=expected,steps=steps+1))
        f.name(b'ABSENT');f.call('empty_begin');f.call('empty_step')
        f.call('empty_step',error=0x93);assert not f.channels
        f.name(b'EMPTY');f.call('empty_begin');f.call('empty_begin',error=0x91)
        f.call('empty_cancel');assert not f.channels
        for location in [0xFFC0,0xFFC6,0xFFCF]:
            f.name(b'EMPTY')
            if location==0xFFC0:
                f.inject[location]=128;f.call('empty_begin',error=0x92)
            else:
                f.call('empty_begin');f.inject[location]=128
                f.call('empty_step',error=0x92)
            assert not f.channels
        result=dict(status='passed',prior_raw_empty_bytes=0,prior_vdrive_c1541_read_bytes=254,
                    terminal_hex='0001',source_version='VICE3.10',
                    source_sha256=hashlib.sha256((PROBE/'vdrive-iec-3.10.c.txt').read_bytes()).hexdigest(),
                    cases=cases,scope='Raw retained-D81 oracle and emitted preflight with modeled ROM; native pending')
        (PROBE/'build/offline-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
    finally:f.close()

def native():
    from vice_config import step,PROJECT
    from vice_plan import run_plan
    s=labels();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    e=ROOT/'agentsworking/evidence/M4'/f'{stamp}-empty-seq';e.mkdir(parents=True)
    disk=e/'working.d81'
    fixtures={b'CONTROL':bytes(range(64)),b'NUL':b'\0',b'IMPORTED':b''}
    cmd=['c1541','-format','emptyprobe,se','d81',str(disk),'-write',str(PROBE/'build/empty-seq.prg'),'emptytest']
    for name,data in fixtures.items():
        p=e/(name.decode()+'.seq');p.write_bytes(data);cmd+=['-write',str(p),name.decode().lower()+',s']
    r=subprocess.run(cmd+['-list'],capture_output=True,text=True,errors='replace');(e/'package.txt').write_text(r.stdout+r.stderr);r.check_returncode()
    shutil.copyfile(disk,e/'initial.d81');before=files(disk.read_bytes())
    for name,data in fixtures.items():assert before[name]['data']==data
    for name in ['empty-seq.prg','empty-seq.lbl','empty-seq.map']:shutil.copyfile(PROBE/'build'/name,e/name)
    canary=bytes((i*73+29)&255 for i in range(1024))
    ready=step('passed','assert.memory',start=s['empty_native_result'],end=s['empty_native_result'],equals_hex='01')
    ready['retry']=dict(max_attempts=20,backoff_ms=100,jitter=False)
    steps=[step('launch','vice.launch',kill_stale=False),step('ready','screen.wait_contains',text='READY.',wait_timeout_s=30),
           step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' ')),
           step('boot','input.sequence',keys=list(b'LOAD"EMPTYTEST",8,1\rRUN\r'),inter_key_delay_s=0.04),
           step('finished','screen.wait_contains',text='EMPTY SEQ NATIVE',wait_timeout_s=30),
           step('diagnostic','dump.memory_ranges',ranges=[dict(label='state',start=0xC000,end=s['__BSS_RUN__']+s['__BSS_SIZE__']-1)]),
           step('diagnostic_capture','monitor.command',command=f'raw: screenshot \"{e}/diagnostic-empty.png\" 2'),ready,
           step('channels','assert.memory',start=0x98,end=0x98,equals_hex='00'),
           step('shim','assert.memory',start=0xC600,end=0xC9FF,equals_hex=canary.hex(' ')),
           step('state','dump.memory_ranges',ranges=[dict(label='state',start=0xC000,end=s['__BSS_RUN__']+s['__BSS_SIZE__']-1)]),
           step('capture','monitor.command',command=f'raw: screenshot "{e}/native-empty.png" 2')]
    plan=dict(version=1,kind='vice_task_plan',plan_id=f'empty-seq-{stamp}',run_mode='gui_vice',global_defaults=dict(
        monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,
        retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),
        artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),
        vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,
                  close_vice=True,headless=True,speed_percent=100)),steps=steps)
    b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
    (e/'harness-build.txt').write_text(b.stdout+b.stderr);b.check_returncode()
    artifacts,manifest=run_plan(plan,e)
    state=(artifacts/'stages/state/state.bin').read_bytes();get=lambda n,w=1:state[s[n]-0xC000:s[n]-0xC000+w]
    assert get('empty_native_stage')==b'\x07' and get('empty_native_done',2)==b'\0\0'
    assert get('empty_native_eof')==b'\x40' and get('empty_native_byte')==b'\xa7'
    assert get('se_io_mode')==b'\0' and get('empty_phase')==b'\0' and get('se_io_owned_temp')==b'\0'
    after=files(disk.read_bytes());assert after[b'EMPTYFINAL']['data']==b'' and b'EMPTYPROBE' not in after
    for name,data in fixtures.items():
        assert after[name]['data']==data
        assert after[name]['chain']==before[name]['chain'],name
    result=dict(status='passed',evidence=str(e),manifest=str(manifest),reader_path='raw-U1 first-block metadata preflight then real SEQ OPEN/read_chunk/close',
                native_empty_bytes=0,imported_empty_bytes=0,empty_read_done=0,empty_read_eof=64,
                nul_bytes=1,control_bytes=64,original_fixture_sectors_unchanged=True,shim_bytes=1024,channels_closed=True,
                prg_sha256=hashlib.sha256((e/'empty-seq.prg').read_bytes()).hexdigest(),
                screenshot=str(e/'native-empty.png'),screenshot_review='pending',
                scope='D81 unpartitioned1581/.NET VICEwarp/traps only; existing provider writer98 guard unchanged; probe bypasses it explicitly')
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    if '--vice' in sys.argv:native()
    else:offline()
