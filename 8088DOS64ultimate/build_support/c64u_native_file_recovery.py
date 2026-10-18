"""Opt-in development native-file REU recovery. Importing performs no I/O to devices."""
import ftplib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import quote
import uuid
import zlib
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'build_support'))
from c64u_probe import Client,speed_option
from c64u_bulk_reu_recovery import Service,SIZE,verify_backup,dump,durable_write,sha
from c64u_ftp_put_transport import FtpPutClient,BASE,valid_id,valid_sha

BASE_SHA='38806976236c39df7b392b8dbf5312adb92c4ac4f9ac60460f664a3eb61e905b'
SERVICE_SHA='40fe690953c245c8093c7cd5e5cb91684df7290602d8afa44dbd2e0b5b30d09e'
CONFIG=0x1985
OFFSET=CONFIG-0x801+2
CONFIG_SIZE=138
MAILBOX=0x6000
DYNAMIC=(0x12b9,0x135f)
LEAVES={'backup':'BACKUP.REU','restore':'REU-FILE-RESTORE.PRG'}
PURPOSE='owned-native-whole-reu-restoration'


def base_prg(path):
    body=Path(path).read_bytes()
    if len(body)!=4624 or sha(body)!=BASE_SHA:raise ValueError('Unpatched native restore PRG differs from reviewed388069 identity')
    if body[OFFSET:OFFSET+CONFIG_SIZE]!=b'DRF1'+bytes(134):raise ValueError('Reviewed disabled DRF configuration differs')
    return body


def configure(base,data,path):
    if not isinstance(base,bytes) or sha(base)!=BASE_SHA:raise ValueError('Unreviewed base restore PRG')
    if not isinstance(data,bytes) or len(data)!=SIZE:raise ValueError('Exact immutable4MiB backup required')
    encoded=path.encode('ascii')+b'\0'
    if not 2<=len(encoded)<=128 or any(b<32 or b>126 for b in encoded[:-1]):raise ValueError('Invalid bounded ASCII restore path')
    result=bytearray(base)
    result[OFFSET+4:OFFSET+CONFIG_SIZE]=bytes([0xa5,len(encoded)])+(zlib.crc32(data)&0xffffffff).to_bytes(4,'little')+encoded+bytes(128-len(encoded))
    return bytes(result)


def validate_stage(record,base,configured,data):
    if not all(isinstance(v,bytes) for v in (base,configured,data)) or len(data)!=SIZE or sha(base)!=BASE_SHA:raise ValueError('Immutable reviewed base/configured PRG and whole backup required')
    run_id=record.get('run_id');directory=BASE+'/'+str(run_id)
    if record.get('schema')!=1 or record.get('purpose')!=PURPOSE or record.get('status')!='verified' or record.get('project')!='8088DOS64ultimate':raise ValueError('Native backup staging is not verified')
    if not valid_id(run_id) or record.get('remote_directory')!=directory or record.get('created_directory') is not True or record.get('source_unchanged') is not True:raise ValueError('Fresh owned unchanged source required')
    if record.get('base_prg_sha256')!=BASE_SHA or record.get('backup_crc32')!=zlib.crc32(data)&0xffffffff:raise ValueError('Staged source/base identity differs')
    if not valid_sha(record.get('marker_sha256')) or record.get('marker_readback_sha256')!=record['marker_sha256'] or not 1<=record.get('marker_bytes',0)<=4096:raise ValueError('Owner marker lacks exact readback')
    if set(record.get('files',{}))!=set(LEAVES):raise ValueError('Exactly backup and configured restore PRG required')
    for role,body in [('backup',data),('restore',configured)]:
        item=record['files'][role];digest=sha(body)
        if item.get('sha256')!=digest or item.get('bytes')!=len(body) or item.get('remote_readback_sha256')!=digest or item.get('remote_readback_bytes')!=len(body) or item.get('remote_path')!=directory+'/'+LEAVES[role]:raise ValueError('Staged file differs from full independently verified bytes')
    if configured!=configure(base,data,record['files']['backup']['remote_path']):raise ValueError('Configured PRG has unapproved bytes or wrong backup binding')


class Budget:
    def __init__(self,clock,seconds):
        if not 1<=seconds<=600:raise ValueError('Recovery phase must be bounded1..600seconds')
        self.clock=clock;self.deadline=clock()+seconds
    def remaining(self):
        left=self.deadline-self.clock()
        if left<=0:raise TimeoutError('Native FTP/restore/reload/full-compare600phase exhausted')
        return left


class DeadlineClient(Client):
    """Private actual REST client clamps each socket wait to remaining phase."""
    budget=None
    def request(self,method,route,data=None,content_type=None):
        timeout=min(5,self.budget.remaining()) if self.budget else 5
        headers={'Content-Type':content_type} if content_type else {}
        request=urllib.request.Request(self.url+route,data=data,method=method,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=timeout) as response:
                raw=response.read()
                if self.budget:self.budget.remaining()
                if response.headers.get('Content-Type','').startswith('application/json'):
                    value=json.loads(raw)
                    if value.get('errors'):raise RuntimeError(f'{route}: {value["errors"]}')
                    return value
                return raw
        except urllib.error.HTTPError as error:
            # Preserve the primary HTTP failure; do not replace it with a late hash/read.
            raise RuntimeError(f'{method} {route}: HTTP{error.code}') from error


class NativeFileClient(FtpPutClient):
    """Adds exactly one current, backup-bound third PRG; no unknown fallback."""
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.native=None;self.paused=False;self.cleared=False;self.budget=None;self.used_directories=set();self.native_used=False
    def bind_budget(self,budget):
        self.budget=budget
        if isinstance(self.client,DeadlineClient):self.client.budget=budget
    def _bound(self):
        if self.budget:self.budget.remaining()
    def get(self,route):self._bound();value=super().get(route);self._bound();return value
    def read(self,address,length):self._bound();value=super().read(address,length);self._bound();return value
    def configs(self,value):self._bound();result=super().configs(value);self._bound();return result
    def put(self,route):
        self._bound();value=super().put(route)
        if route=='machine:pause':self.paused=True
        elif route in ('machine:resume','machine:reset'):self.paused=False
        self._bound();return value
    def register(self,record,base,configured,data):
        validate_stage(record,base,configured,data)
        if record['remote_directory'] in self.used_directories:raise ValueError('A native recovery registration must use a fresh independent stage')
        self.used_directories.add(record['remote_directory']);self.native_used=False
        self.native=(configured,record['files']['restore']['remote_path']);self.cleared=False
    def forget(self):self.native=None;self.cleared=False
    def clear_mailbox(self):
        self._bound()
        if not self.paused or self.native is None or self.native_used:raise ValueError('Native mailbox clear requires paused machine and verified current registration')
        self.client.put('machine:writemem?address=6000&data='+bytes(32).hex().upper());self._bound()
        if self.read(MAILBOX,32)!=bytes(32):raise ValueError('Fresh DRF mailbox clear readback mismatch')
        self.cleared=True;self.journal('native_fresh_mailbox_cleared',address=MAILBOX,bytes=32)
    def request(self,method,route,data=None,content_type=None):
        self._bound()
        if method=='POST' and route=='runners:run_prg' and self.native is not None and data==self.native[0]:
            if not isinstance(data,bytes) or content_type!='application/octet-stream' or not self.paused or not self.cleared or self.native_used:raise ValueError('Native file launch needs exact immutable registration and fresh paused mailbox clear')
            path=self.native[1];self.cleared=False;self.native_used=True
            value=self.client.put('runners:run_prg?file='+quote(path,safe=''));self.paused=False
            self.stats['put_prg_launches']+=1;self.journal('native_restore_file_run',sha256=sha(data),path=path)
        else:value=super().request(method,route,data,content_type)
        self._bound();return value


def stage_backup(ftp_factory,backup_path,backup_manifest,data,base,run_id,output,budget):
    """Fresh directory, marker and full byte readback. Never DELETE/rename/mount."""
    if not valid_id(run_id):raise ValueError('Invalid fresh native recovery run id')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    directory=BASE+'/'+run_id;configured=configure(base,data,directory+'/'+LEAVES['backup'])
    blobs={'backup':data,'restore':configured}
    record={'schema':1,'project':'8088DOS64ultimate','purpose':PURPOSE,'run_id':run_id,'remote_directory':directory,
            'status':'running','created_directory':False,'source_unchanged':False,'base_prg_sha256':BASE_SHA,
            'backup_crc32':zlib.crc32(data)&0xffffffff,'files':{role:{'sha256':sha(body),'bytes':len(body),'remote_path':directory+'/'+LEAVES[role]} for role,body in blobs.items()}}
    def save():dump(output/'native-file-staging.json',record)
    def source_check():
        budget.remaining()
        if Path(backup_path).stat().st_mode&0o222:raise ValueError('Backup source must remain read-only')
        if verify_backup(Path(backup_path),backup_manifest)!=data:raise ValueError('Immutable backup source changed')
    ftp=None;primary=None
    def bound(*_):budget.remaining()
    def network_bound():
        seconds=min(20,budget.remaining());ftp.timeout=seconds
        if getattr(ftp,'sock',None) is not None:ftp.sock.settimeout(seconds)
    def readback(path,expected):
        found=bytearray()
        def collect(block):
            bound()
            if len(found)+len(block)>len(expected):raise ValueError('FTP readback has extra bytes')
            found.extend(block)
        network_bound();ftp.retrbinary('RETR '+path,collect);bound()
        if bytes(found)!=expected:raise ValueError('FTP byte/length readback mismatch')
        return bytes(found)
    save()
    try:
        source_check();ftp=ftp_factory(min(20,budget.remaining()));bound();network_bound()
        # BASE is established by the already verified two-PRG staging. Do not
        # swallow an ambiguous MKD error or reuse any existing pass directory.
        ftp.cwd(BASE);bound();network_bound();ftp.mkd(directory);record['created_directory']=True;save()
        marker=json.dumps({'schema':1,'project':record['project'],'purpose':PURPOSE,'run_id':run_id,
                           'nonce':str(uuid.uuid4()),'files':{k:v['sha256'] for k,v in record['files'].items()}},sort_keys=True).encode()
        network_bound();ftp.storbinary('STOR '+directory+'/OWNER.JSON',io.BytesIO(marker),callback=bound)
        found=readback(directory+'/OWNER.JSON',marker)
        record.update(marker_sha256=sha(marker),marker_readback_sha256=sha(found),marker_bytes=len(marker));save()
        for role,body in blobs.items():
            network_bound();ftp.storbinary('STOR '+record['files'][role]['remote_path'],io.BytesIO(body),callback=bound)
            found=readback(record['files'][role]['remote_path'],body)
            record['files'][role].update(remote_readback_bytes=len(found),remote_readback_sha256=sha(found));save()
        source_check();record.update(source_unchanged=True,status='verified');validate_stage(record,base,configured,data)
    except Exception as error:
        primary=error;record.update(status='failed',error=repr(error));raise
    finally:
        late=None
        if ftp is not None:
            try:ftp.close() # No potentially blocking QUIT after expiry.
            except Exception as error:late=error;record.setdefault('cleanup_errors',[]).append(repr(error))
        if late is not None:record['status']='failed'
        try:save()
        except Exception as error:
            if primary is None:raise
        if primary is None and late is not None:raise late
    durable_write(output/'configured-restore.prg',configured)
    return record,configured


def resident_identity(ram,configured,terminal=False):
    if not isinstance(ram,bytes) or len(ram)!=65536:raise ValueError('Native identity requires full exact C64 RAM capture')
    for address in DYNAMIC:
        value=int.from_bytes(ram[address:address+2],'little')
        window=(0xc100,0xc47f) if address==DYNAMIC[0] else (0xc480,0xc7ff)
        # Pause may land between low/high STA operands. First upload can
        # temporarily retain FFhigh (path command<=131bytes); first drain
        # FF80 and C4FF->C500 low-first seam C400 are also known publications.
        transient=(value==0xffff or (address==DYNAMIC[0] and 0xff00<=value<=0xff00+configured[OFFSET+5]+2) or (address==DYNAMIC[1] and value in (0xff80,0xc400)))
        if terminal and value!=(0xc101 if address==DYNAMIC[0] else 0xc67f):raise ValueError('Native final CLOSE/512byte READ operand identity mismatch')
        if not (window[0]<=value<=window[1] or (not terminal and transient)):raise ValueError('Native dynamic UCI operand escaped expected buffer')
    ignored={a+i for a in DYNAMIC for i in (0,1)}
    for offset,expected in enumerate(configured[2:]):
        address=0x801+offset
        if address not in ignored and ram[address]!=expected:raise ValueError(f'Native resident PRG differs at${address:04X}')


def done_mailbox(raw,data):
    if len(raw)!=32 or raw[:4]!=b'DRF1' or raw[4]!=0xa5:raise ValueError('Native restore did not publish fresh DONE')
    crc=(zlib.crc32(data)&0xffffffff).to_bytes(4,'little')
    if raw[5:7]!=bytes(2) or raw[7]!=6 or raw[8:12]!=bytes(4) or raw[16:20]!=crc or raw[20:24]!=crc or raw[28:30]!=b'\0\x20' or int.from_bytes(raw[24:28],'little')>=144323:raise ValueError('Native DONE lacks exact4MiB/CRC/known-CLOSE counters')


class NativeFileService(Service):
    def __init__(self,client,prg,journal,*,base,ftp_factory,backup_path,output,backup_manifest=None,clock=time.monotonic,sleep=time.sleep,run_id_factory=None):
        if not isinstance(client,NativeFileClient) or sha(base)!=BASE_SHA or sha(prg)!=SERVICE_SHA:raise ValueError('Reviewed native-file adapter/base/original DRS1 service required')
        super().__init__(client,prg,journal,clock=clock,sleep=sleep);client.journal=journal
        self.base=base;self.ftp_factory=ftp_factory;self.backup_path=Path(backup_path);self.output=Path(output)
        self.backup_manifest=backup_manifest;self.attempt=0;self.phase=None
        self.run_id_factory=run_id_factory or (lambda attempt:'reu-native-'+uuid.uuid4().hex+'-p'+str(attempt))
    def _capture(self,name):
        # Failure evidence gets its own bounded REST requests, without extending
        # the expired restoration phase or masking the earlier error.
        budget=self.client.budget;self.client.bind_budget(None)
        try:
            self.client.put('machine:pause');ram=self.client.read(0,65536);durable_write(self.output/name,ram)
            raw=ram[MAILBOX:MAILBOX+32]
            dump((self.output/name).with_suffix('.json'),{'ram_sha256':sha(ram),'bytes':len(ram),'mailbox_hex':raw.hex(),'native_handle':raw[8] if raw[:4]==b'DRF1' else None,'native_cleanup_error':raw[9] if raw[:4]==b'DRF1' else None,'before_any_further_service_overwrite':True})
            self.journal('native_failure_ram_captured',file=name,sha256=sha(ram));return ram
        except Exception as error:self.journal('native_failure_ram_capture_failed',file=name,error=repr(error));return None
        finally:self.client.bind_budget(budget)
    def _snapshot(self,name,configured,terminal=False):
        self.client.put('machine:pause');ram=self.client.read(0,65536);durable_write(self.output/name,ram)
        resident_identity(ram,configured,terminal);self.phase.remaining();return ram
    def restore(self,data,phase_seconds=600):
        self.attempt+=1
        if self.attempt>2:raise ValueError('Native recovery permits at most two fresh whole attempts')
        self.phase=Budget(self.clock,phase_seconds);self.client.bind_budget(self.phase);self.client.forget()
        try:
            machine=self.client.get('configs/C64%20and%20Cartridge%20Settings')
            settings=machine['C64 and Cartridge Settings'];size=str(settings.get('REU Size','')).split()
            if settings.get('Command Interface')!='Enabled' or settings.get('RAM Expansion Unit')!='Enabled' or len(size)!=2 or size[1]!='MB' or not size[0].isdigit() or int(size[0])<4:raise ValueError('Actual enabled Command Interface/minimum4MiB REU required; no settings changed')
            turbo=self.client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
            if turbo.get('System Mode')!='PAL':raise ValueError('Actual System Mode must be PAL for frozen native clock bounds')
            if turbo.get('Turbo Control')!='Manual' or str(turbo.get('CPU Speed')).strip()!='64':
                options=self.client.get('configs/U64%20Specific%20Settings/CPU%20Speed')['U64 Specific Settings']['CPU Speed']['values']
                self.client.configs({'U64 Specific Settings':{'Turbo Control':'Manual','CPU Speed':speed_option(options,64)}})
            active=self.client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
            if active.get('System Mode')!='PAL' or active.get('Turbo Control')!='Manual' or str(active.get('CPU Speed')).strip()!='64':raise ValueError('Verified PAL/Manual64 recovery execution required')
            dump(self.output/f'native-preflight-{self.attempt}.json',{'machine':machine,'turbo_before_pass':turbo,'turbo_active':active,'native_base':'DF1C','native_id_validation':'Real UCI I/O validates identity before control writes','machine_settings_changed':False,'turbo_restored_by_outer_cleanup':True})
            manifest=self.backup_manifest or json.loads(self.backup_path.with_suffix('.json').read_text())
            if not isinstance(data,bytes) or verify_backup(self.backup_path,manifest)!=data:raise ValueError('Restore bytes differ from immutable local backup')
            run_id=self.run_id_factory(self.attempt);folder=self.output/f'native-restore-{self.attempt}'
            record,configured=stage_backup(self.ftp_factory,self.backup_path,manifest,data,self.base,run_id,folder,self.phase)
            self.client.register(record,self.base,configured,data)
            self.client.put('machine:pause');self.client.clear_mailbox()
            self.client.request('POST','runners:run_prg',configured,'application/octet-stream');self.client.put('machine:resume')
            seen_active=False;identity_checked=False;startup_end=min(self.phase.deadline,self.clock()+12)
            while True:
                self.phase.remaining()
                if not seen_active and self.clock()>=startup_end:raise TimeoutError('Native restore did not publish fresh startup within12seconds')
                raw=self.client.read(MAILBOX,32)
                if raw[:4]==b'DRF1':
                    if raw[4]==0xe1:raise RuntimeError('Native restore failure: '+raw.hex())
                    if raw[4] in (1,2):
                        seen_active=True
                        if not identity_checked:
                            self._snapshot(f'native-start-ram-{self.attempt}.bin',configured);identity_checked=True;self.client.put('machine:resume')
                    elif raw[4]==0xa5:
                        if not seen_active:raise ValueError('Native DONE without observed fresh initialization/busy state')
                        ram=self._snapshot(f'native-done-ram-{self.attempt}.bin',configured,True)
                        done_mailbox(ram[MAILBOX:MAILBOX+32],data)
                        dump(folder/'native-done.json',{'mailbox_hex':ram[MAILBOX:MAILBOX+32].hex(),'configured_prg_sha256':sha(configured),'base_prg_sha256':BASE_SHA,'backup_sha256':sha(data),'backup_crc32':zlib.crc32(data)&0xffffffff,'elapsed_host_seconds':phase_seconds-self.phase.remaining()})
                        break
                    elif raw[4]!=0 or seen_active:raise ValueError('Unknown native DRF state')
                elif seen_active or raw[:4] not in (bytes(4),b'D\0\0\0',b'DR\0\0',b'DRF\0'):raise ValueError('Fresh native mailbox identity mismatch')
                self.sleep(min(0.05,self.phase.remaining()))
            if self.backup_path.stat().st_mode&0o222 or verify_backup(self.backup_path,manifest)!=data:raise ValueError('Local backup changed during native restore')
            self.phase.remaining()
            # A5 never substitutes for original service code/READY and all4MiB readback.
            self.load();self.phase.remaining()
            self.journal('native_restore_done_service_reloaded',attempt=self.attempt,independent_full_compare_required=True)
        except Exception:
            self._capture(f'native-restore-failure-{self.attempt}-before-service.bin');self.client.bind_budget(None);self.client.forget();raise
    def compare(self,data,output,phase_seconds=600):
        if self.phase is None:raise ValueError('Native restore phase not established')
        try:
            result=super().compare(data,output,phase_seconds=min(phase_seconds,self.phase.remaining()))
            manifest=self.backup_manifest or json.loads(self.backup_path.with_suffix('.json').read_text())
            if self.backup_path.stat().st_mode&0o222 or verify_backup(self.backup_path,manifest)!=data:raise ValueError('Local backup changed during full comparison')
            self.phase.remaining();self.journal('native_restore_full_phase_verified',attempt=self.attempt,sha256=result)
            return result
        except Exception:
            self._capture(f'native-compare-failure-{self.attempt}-before-reset.bin');raise
        finally:self.client.bind_budget(None);self.client.forget();self.phase=None
