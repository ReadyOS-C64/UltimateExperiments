"""Unshipped opt-in HD evidence retention; importing contacts no device.

The reviewed caller still owns physical execution. This collector never uploads
an HD image, writes REU, deletes remote files, or restores an HD image. It saves
new-run authority before the existing first-4MiB recovery discards that authority.
"""
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import signal
import threading
import time

from c64u_bulk_reu_recovery import Service, dump, evidence_error

# Pin the existing original service, rather than an arbitrary evidence executable.
SERVICE_SHA='40fe690953c245c8093c7cd5e5cb91684df7290602d8afa44dbd2e0b5b30d09e'
RANGES=(('authoritative-sector.bin',0x350000),('guest-handoff.bin',0x352000))

def sha(data):return hashlib.sha256(data).hexdigest()

def exact_file(path,data):
    with Path(path).open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    if Path(path).read_bytes()!=data:raise OSError('Local evidence readback differs')
    os.chmod(path,0o444)


def stop_and_reap(child):
    """Every child lifecycle exit attempts bounded termination and reaping.

    A process-control exception, including a repeated interrupt, is retained;
    it never prevents the parent from proceeding to machine recovery. The raw
    PID fallback is restricted to this child's PID, never a process group.
    """
    errors=[];alive=True;pid=None;reaped=False
    try:pid=child.pid
    except BaseException as error:errors.append(evidence_error(error))
    try:alive=child.is_alive()
    except BaseException as error:errors.append(evidence_error(error))
    if alive:
        try:child.kill()
        except BaseException as error:
            errors.append(evidence_error(error))
            if type(pid) is int and pid>0:
                try:os.kill(pid,signal.SIGKILL)
                except BaseException as error:errors.append(evidence_error(error))
    try:
        child.join(2)
        reaped=not child.is_alive()
    except BaseException as error:errors.append(evidence_error(error))
    if not reaped and type(pid) is int and pid>0:
        deadline=time.monotonic()+2;raw_faults=0
        while time.monotonic()<deadline:
            try:
                waited,_=os.waitpid(pid,os.WNOHANG)
                if waited==pid:reaped=True;break
                time.sleep(0.01)
            except ChildProcessError:reaped=True;break
            except BaseException as error:
                errors.append(evidence_error(error));raw_faults+=1
                if raw_faults>=2:break
    if not reaped:errors.append({'type':'ChildCleanupError','error':'Child reaping could not be confirmed','cancelled':False})
    return {'reaped':reaped,'errors':errors}

class HdEvidenceCollector:
    """Only explicit, previously verified disposable HD ownership is accepted.

    Config is the exact140-byte D64H source block pinned in the reviewed PRG.
    Actual runtime/config/map/labels identities remain the Application's checks;
    this additional binding cannot replace those checks or native resident proof.
    The FTP factory receives a bounded timeout and must open a fresh connection.
    """
    def __init__(self,owned,owner_bytes,source,runtime_prg,labels_blob,ftp_factory,seconds=90):
        self.owned=json.loads(json.dumps(owned));self.owner=bytes(owner_bytes)
        self.source=bytes(source);self.runtime_prg=bytes(runtime_prg);self.labels_blob=bytes(labels_blob)
        symbols={name.lstrip('.'):int(address,16) for address,name in re.findall(r'^al ([0-9a-fA-F]+) (\S+)',self.labels_blob.decode('ascii'),re.M)}
        self.resident_config_address=symbols['hdc_state_start']
        offset=symbols['hdc_config']-0x801+2
        if offset<2:raise ValueError('D64H source must be inside the packaged PRG')
        self.config=self.runtime_prg[offset:offset+140]
        self.ftp_factory=ftp_factory;self.seconds=seconds
        self.preflight()

    def preflight(self):
        if isinstance(self.seconds,bool) or not isinstance(self.seconds,(int,float)) or not math.isfinite(self.seconds) or not 1<=self.seconds<=120:
            raise ValueError('Explicit HD evidence phase must be bounded1..120seconds')
        if threading.current_thread() is not threading.main_thread() or threading.active_count()!=1 or 'fork' not in multiprocessing.get_all_start_methods():
            raise ValueError('Isolated evidence requires a single-threaded POSIX main process')
        r=self.owned
        if self.runtime_prg[:2]!=b'\x01\x08' or r.get('runtime_prg_sha256')!=sha(self.runtime_prg) or r.get('labels_sha256')!=sha(self.labels_blob) or not 0xea00<=self.resident_config_address<=0xed78:
            raise ValueError('Exact reviewed configured PRG/labels and resident config address required')
        if r.get('schema')!=1 or r.get('project')!='8088DOS64ultimate' or r.get('purpose')!='owned-disposable-hd-evidence' or r.get('status')!='verified' or r.get('created_directory') is not True or r.get('original_source_unchanged') is not True:
            raise ValueError('Explicit fresh verified disposable HD ownership is required')
        run=r.get('run_id')
        if not isinstance(run,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',run):raise ValueError('Invalid fresh run id')
        directory='/usb1/DOS64_TEST/'+run
        if r.get('remote_directory')!=directory or r.get('native_path')!=directory+'/DOSHD.IMG':raise ValueError('HD path must be exactly the fresh owned image')
        marker=json.loads(self.owner)
        if not 1<=len(self.owner)<=4096 or sha(self.owner)!=r.get('marker_sha256') or r.get('marker_readback_sha256')!=sha(self.owner) or marker.get('project')!='8088DOS64ultimate' or marker.get('run_id')!=run or marker.get('purpose')!=r['purpose'] or marker.get('image_sha256')!=sha(self.source) or not re.fullmatch(r'[0-9a-f]{32}',str(marker.get('nonce'))):
            raise ValueError('Ownership marker/source binding is incomplete')
        if type(r.get('profile')) is not int or r['profile'] not in (0,1):raise ValueError('Only2/20MiB profiles are accepted')
        profile=r['profile'];size=(2 if profile==0 else 20)*1024*1024
        if len(self.source)!=size or r.get('source_bytes')!=size or r.get('source_sha256')!=sha(self.source) or r.get('remote_readback_bytes')!=size or r.get('remote_readback_sha256')!=sha(self.source) or self.source[510:512]!=b'\x55\xaa':raise ValueError('Expected complete bootable source image/readback required')
        path=r['native_path'].encode('ascii')+b'\0';c=self.config
        if len(c)!=140 or c[:5]!=b'D64H\xa5' or c[5] not in (0,1) or c[6]!=profile or c[7] not in (0,1) or c[8]!=0x80 or c[9] not in (1,2) or not 1<=c[10]<=32 or c[11]!=len(path) or c[12:12+len(path)]!=path or any(c[12+len(path):]):raise ValueError('Exact enabled HD-only/HD-first config/path/profile/read-only binding required')
        if r.get('readonly')!=c[7] or type(r.get('readonly')) is not int or r.get('config_sha256')!=sha(c):raise ValueError('Read-only/config identity differs')
        return True

    def collect(self,client,prg,output,journal):
        """Child-only transport work. RAM precedes any helper upload."""
        output=Path(output);output.mkdir(exist_ok=False)
        deadline=time.monotonic()+self.seconds
        record={'schema':1,'status':'running','evidence_only':True,'artifacts':{},'errors':[],
                'source_sha256':sha(self.source),'config_sha256':sha(self.config),
                'owned':self.owned,'phase_seconds':self.seconds,
                'limitations':['Remote readback is a visible-file snapshot, not durable media proof',
                    'Only two REU sectors are retained; broader dirty cache/guest state may require additional capture',
                    'REU restoration does not restore remote HD contents or prior CPU execution',
                    'No physical guest AH03 trace is collected by this hook']}
        def bound():
            left=deadline-time.monotonic()
            if left<=0:raise TimeoutError('HD evidence phase exhausted')
            return left
        def save():dump(output/'evidence.json',record)
        def retain(name,data,**meta):
            bound();exact_file(output/name,data);bound()
            record['artifacts'][name]={'bytes':len(data),'sha256':sha(data),**meta};save()
        ram_ok=False
        try:
            bound();client.put('machine:pause');ram=client.read(0,65536)
            if not isinstance(ram,bytes) or len(ram)!=65536:raise ValueError('Complete failure RAM required before evidence helper')
            retain('ram-before-evidence-helper.bin',ram);ram_ok=True
            address=self.resident_config_address
            copied=ram[address:address+136]
            record['resident_config']={'address':address,'sha256':sha(copied),'matches_planned_source':copied==self.config[4:]}
            if copied!=self.config[4:]:
                record['errors'].append({'scope':'resident_config','error':'Captured resident D64H path/profile/read-only copy differs from reviewed source'})
            save()
        except Exception as error:record['errors'].append({'scope':'ram','error':repr(error)});save()
        if ram_ok:
            try:
                if sha(prg)!=SERVICE_SHA:raise ValueError('Original reviewed40fe DRS1 service required')
                service=Service(client,prg,journal,command_seconds=min(12,bound()))
                service.load();bound()
                for name,address in RANGES:
                    service.command_seconds=min(12,bound())
                    data=service.command(1,address,512)
                    if not isinstance(data,bytes) or len(data)!=512:raise ValueError('Exact512-byte authority readback required')
                    retain(name,data,reu_start=address)
                service.check_code();bound()
            except Exception as error:record['errors'].append({'scope':'reu','error':repr(error)});save()
        else:record['errors'].append({'scope':'reu','error':'Skipped helper to preserve uncaptured RAM'})
        try:
            # Paused guest cannot continue UCI writes while its file is read.
            bound();client.put('machine:pause')
            with self.ftp_factory(min(5,bound())) as ftp:
                marker=bytearray()
                def owner_block(block):
                    bound()
                    if len(marker)+len(block)>4096:raise ValueError('Owner marker exceeds bound')
                    marker.extend(block)
                ftp.retrbinary('RETR '+self.owned['remote_directory']+'/OWNER.JSON',owner_block)
                if bytes(marker)!=self.owner:raise ValueError('Remote owner marker changed; image read forbidden')
                retain('owner-readback.json',bytes(marker))
                partial=output/'hd-visible.partial.img';digest=hashlib.sha256();count=0
                with partial.open('xb') as stream:
                    def image_block(block):
                        nonlocal count
                        bound()
                        if count+len(block)>len(self.source):raise ValueError('Remote HD image exceeds expected exact length')
                        stream.write(block);stream.flush();os.fsync(stream.fileno())
                        digest.update(block);count+=len(block)
                    try:ftp.retrbinary('RETR '+self.owned['native_path'],image_block)
                    finally:stream.flush();os.fsync(stream.fileno())
                bound()
                if count!=len(self.source):raise ValueError('Remote HD image is truncated')
                if sha(partial.read_bytes())!=digest.hexdigest():raise OSError('Local complete image readback differs')
                complete=output/'hd-visible.img';partial.rename(complete);os.chmod(complete,0o444)
                record['artifacts']['hd-visible.img']={'bytes':count,'sha256':digest.hexdigest(),'source_equal':digest.hexdigest()==sha(self.source)}
                if self.config[7] and digest.hexdigest()!=sha(self.source):raise ValueError('Read-only image changed')
        except Exception as error:record['errors'].append({'scope':'ftp','error':repr(error)})
        record['status']='passed' if not record['errors'] else 'failed';save()
        return record

    def run(self,client,prg,output,journal):
        """Parent deadline also stops a blocked socket/FTP implementation.

        Fork is deliberately restricted to a reviewed single-threaded POSIX CLI.
        The child has no recovery-write capability in this collector. After any
        timeout the parent reloads its independent recovery service normally.
        """
        self.preflight();destination=Path(output)/'hd-before-restore'
        def worker():
            try:self.collect(client,prg,destination,journal)
            except BaseException:os._exit(70)
        child=multiprocessing.get_context('fork').Process(target=worker,daemon=True)
        started=time.monotonic();timed_out=False;lifecycle_errors=[];cleanup=None
        try:
            child.start();child.join(self.seconds);timed_out=child.is_alive()
        except BaseException as error:lifecycle_errors.append(evidence_error(error))
        finally:
            # Also executes for interrupts during join/start, unlike the original
            # proposal. Cleanup failures themselves cannot abort REU recovery.
            try:cleanup=stop_and_reap(child)
            except BaseException as error:cleanup={'reaped':False,'errors':[evidence_error(error)]}
        # A killed process cannot issue new userspace device operations. An OS
        # uninterruptible kernel operation remains outside Python guarantees.
        result={'status':'failed','isolated':True,'timed_out':timed_out,'child_exitcode':child.exitcode,
                'elapsed_seconds':time.monotonic()-started,'evidence_directory':str(destination),
                'lifecycle_errors':lifecycle_errors,'child_cleanup':cleanup,
                'cancelled':any(item.get('cancelled') for item in lifecycle_errors+cleanup['errors'])}
        path=destination/'evidence.json'
        if path.exists() and path.stat().st_size<=65536:
            record=json.loads(path.read_text());result['collection']=record
            expected={'ram-before-evidence-helper.bin':65536,'authoritative-sector.bin':512,
                      'guest-handoff.bin':512,'owner-readback.json':len(self.owner),'hd-visible.img':len(self.source)}
            artifacts=record.get('artifacts',{})
            if not isinstance(artifacts,dict) or not set(artifacts)<=set(expected):raise ValueError('Invalid child artifact set')
            verified=[]
            # Independently verify every declared complete artifact, including
            # artifacts retained in failed/timed-out collections.
            for name,item in artifacts.items():
                target=destination/name
                if target.is_symlink():raise ValueError('Evidence artifact must not be a symlink')
                body=target.read_bytes();length=expected[name]
                if len(body)!=length or item.get('bytes')!=length or item.get('sha256')!=sha(body):raise ValueError('Independent parent evidence readback differs: '+name)
                if name=='owner-readback.json' and body!=self.owner:raise ValueError('Parent owner readback differs')
                verified.append(name)
            result['parent_verified_artifacts']=verified
            complete=set(verified)==set(expected)
            result['parent_all_artifacts_verified']=complete
            if complete:
                ram=(destination/'ram-before-evidence-helper.bin').read_bytes();address=self.resident_config_address
                result['parent_resident_config_matches']=ram[address:address+136]==self.config[4:]
            if not timed_out and child.exitcode==0 and not lifecycle_errors and not cleanup['errors'] and cleanup['reaped'] and record.get('status')=='passed' and complete and result.get('parent_resident_config_matches'):
                result['status']='passed'
        journal('hd_pre_restore_evidence',**result)
        return result
