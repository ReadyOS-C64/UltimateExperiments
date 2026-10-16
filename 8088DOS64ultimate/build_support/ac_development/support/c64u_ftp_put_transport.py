"""Development transport: verified FTP PRGs plus attachment-free PUT.

Never edits firmware /Temp or mounts media; explicit turbo controls are allowed. The
unchanged application/recovery code sees a Client-compatible adapter. Only its
known POST-shaped calls are translated; no POST is sent to the device.
"""
import argparse
from datetime import datetime,timezone
import ftplib
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote
import uuid
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'build_support'))
from c64u_probe import Client
from c64u_bulk_reu_recovery import validate_prg,dump

BASE='/usb1/DOS64_TEST'
LEAVES={'recovery':'REU-RECOVERY.PRG','native':'NATIVE-DOS.PRG'}
CATEGORY='U64 Specific Settings'
CONFIG_KEYS={'Turbo Control','CPU Speed'}
READ_ROUTES={'info','drives','configs/U64%20Specific%20Settings',
             'configs/C64%20and%20Cartridge%20Settings',
             'configs/U64%20Specific%20Settings/CPU%20Speed',
             'configs/U64%20Specific%20Settings/Turbo%20Control'}


def sha(data):return hashlib.sha256(data).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def valid_id(value):return isinstance(value,str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',value)
def valid_sha(value):return isinstance(value,str) and re.fullmatch(r'[0-9a-f]{64}',value)


def validate_blob(role,blob):
    if role not in LEAVES or not isinstance(blob,bytes):raise ValueError('Unknown PRG role or nonimmutable payload')
    if role=='recovery':validate_prg(blob)
    elif len(blob)<3 or blob[:2]!=b'\x01\x08' or 0x801+len(blob)-2>0xc000:
        raise ValueError('Native PRG must load contiguous RAM0801..BFFF')


def prepare_prgs(ftp_factory,inputs,run_id,output,clock=time.monotonic,phase_seconds=120):
    """Explicit root-owned staging operation; importing this module is inert.

    inputs: exactly recovery/native -> {path:localPath, sha256:reviewedSHA}.
    Creates a NEW remote directory, verifies marker and every byte of two files.
    No deletion, overwrite of an existing directory, or ambiguous-run reuse.
    """
    if not valid_id(run_id) or not 1<=phase_seconds<=180:raise ValueError('Invalid fresh run id or bounded staging deadline')
    if set(inputs)!=set(LEAVES):raise ValueError('Exactly recovery/native reviewed PRGs are required')
    blobs={};records={}
    for role,item in inputs.items():
        body=Path(item['path']).read_bytes();validate_blob(role,body)
        if not valid_sha(item.get('sha256')) or sha(body)!=item['sha256']:raise ValueError('Local PRG differs from reviewed identity')
        blobs[role]=body;records[role]={'source_path':str(Path(item['path']).resolve()),'sha256':sha(body),'bytes':len(body),
                                      'remote_path':BASE+'/'+run_id+'/'+LEAVES[role]}
    if sha(blobs['native'])==sha(blobs['recovery']):raise ValueError('PRG roles must have distinct reviewed identities')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    record={'schema':1,'project':'8088DOS64ultimate','purpose':'owned-native-development-prgs','status':'running',
            'run_id':run_id,'remote_directory':BASE+'/'+run_id,'created_directory':False,'files':records,
            'source_files_unchanged':False,'started_utc':utc(),'phase_seconds':phase_seconds,
            'limitations':['Development FTP staging only; no C64 or REU execution','Remote files retained; no deletion or unrelated overwrite']}
    def save():dump(output/'prg-staging.json',record)
    deadline=clock()+phase_seconds
    def bound(*_):
        if clock()>=deadline:raise TimeoutError('Owned PRG FTP staging exceeded bounded phase deadline')
    def readback(ftp,path,expected):
        check=bytearray()
        def collect(block):
            bound()
            if len(check)+len(block)>len(expected):raise ValueError('Remote PRG/marker readback has extra bytes')
            check.extend(block)
        ftp.retrbinary('RETR '+path,collect)
        bound()
        if bytes(check)!=expected:raise ValueError('Remote PRG/marker readback differs from every original byte')
        return bytes(check)
    save()
    try:
        bound()
        with ftp_factory() as ftp:
            bound()
            try:ftp.mkd(BASE)
            except ftplib.error_perm:ftp.cwd(BASE)
            bound();ftp.mkd(record['remote_directory']);record['created_directory']=True;save()
            marker=json.dumps({'schema':1,'project':record['project'],'purpose':record['purpose'],'run_id':run_id,
                               'nonce':str(uuid.uuid4()),'files':{k:v['sha256'] for k,v in records.items()}},sort_keys=True).encode()
            marker_path=record['remote_directory']+'/OWNER.JSON'
            ftp.storbinary('STOR '+marker_path,io.BytesIO(marker),callback=bound)
            found=readback(ftp,marker_path,marker)
            record.update(marker_sha256=sha(marker),marker_readback_sha256=sha(found),marker_bytes=len(marker));save()
            for role,body in blobs.items():
                bound();ftp.storbinary('STOR '+records[role]['remote_path'],io.BytesIO(body),callback=bound)
                found=readback(ftp,records[role]['remote_path'],body)
                records[role].update(remote_readback_bytes=len(found),remote_readback_sha256=sha(found));save()
        for role,item in inputs.items():
            bound()
            if Path(item['path']).read_bytes()!=blobs[role]:raise ValueError('Local source PRG changed during FTP staging')
        record['source_files_unchanged']=True;record['status']='verified'
    except Exception as error:record['status']='failed';record['error']=repr(error)
    finally:record['finished_utc']=utc();save()
    return record


class FtpPutClient:
    """Strict adapter around unchanged Client; never falls back to POST.

    PUT chunks are at most128 bytes and allowed only in owned staging/mailboxes.
    A failed/ambiguous write is NOT retried. The original host handshake retains
    full staging/descriptor readback before GO, and all original REU checks.
    """
    def __init__(self,client,manifest,blobs,diag_address,diag_size=19,clock=time.monotonic,write_seconds=15,journal=lambda *a,**k:None):
        if diag_size!=19 or not isinstance(diag_address,int) or not 0xea00<=diag_address<=0xef00-diag_size:
            raise ValueError('Native diagnostic mailbox must be the reviewed19byte device-state range')
        if not 1<=write_seconds<=30:raise ValueError('Memory upload deadline must be bounded1..30seconds')
        if manifest.get('schema')!=1 or manifest.get('project')!='8088DOS64ultimate' or manifest.get('purpose')!='owned-native-development-prgs' or manifest.get('status')!='verified':
            raise ValueError('PRG staging manifest is not independently verified')
        run_id=manifest.get('run_id');directory=BASE+'/'+str(run_id)
        if not valid_id(run_id) or manifest.get('remote_directory')!=directory or manifest.get('created_directory') is not True or manifest.get('source_files_unchanged') is not True:
            raise ValueError('PRGs require a fresh verified owned directory and unchanged local sources')
        if not valid_sha(manifest.get('marker_sha256')) or manifest.get('marker_readback_sha256')!=manifest['marker_sha256'] or not isinstance(manifest.get('marker_bytes'),int) or not 1<=manifest['marker_bytes']<=4096:
            raise ValueError('Ownership marker was not independently read back')
        if set(manifest.get('files',{}))!=set(LEAVES) or set(blobs)!=set(LEAVES):raise ValueError('Exactly two known PRGs must be registered')
        self.paths={}
        for role,blob in blobs.items():
            validate_blob(role,blob);item=manifest['files'][role];digest=sha(blob)
            if not valid_sha(item.get('sha256')) or item['sha256']!=digest or item.get('bytes')!=len(blob) or item.get('remote_readback_bytes')!=len(blob) or item.get('remote_readback_sha256')!=digest or item.get('remote_path')!=directory+'/'+LEAVES[role]:
                raise ValueError('PRG registry does not match exact independently read-back owned bytes')
            if digest in self.paths:raise ValueError('PRG identities must be distinct')
            self.paths[digest]=item['remote_path']
        self.client=client;self.clock=clock;self.write_seconds=write_seconds;self.journal=journal
        self.diag=(diag_address,diag_address+diag_size);self.stats={'put_memory_requests':0,'put_prg_launches':0,'put_config_requests':0}
    def get(self,route):
        if route not in READ_ROUTES:raise ValueError('Read route is outside this development workflow')
        return self.client.get(route)
    def read(self,address,length):
        if not isinstance(address,int) or not isinstance(length,int) or not 0<=address<65536 or not 1<=length<=65536-address:raise ValueError('Invalid bounded C64 memory read')
        value=self.client.read(address,length)
        if not isinstance(value,bytes) or len(value)!=length:raise ValueError('Underlying C64 memory read length mismatch')
        return value
    def put(self,route):
        if route not in ('machine:pause','machine:resume','machine:reset'):raise ValueError('Direct PUT route is outside this development workflow')
        return self.client.put(route)
    def configs(self,value):
        if not isinstance(value,dict) or set(value)!={CATEGORY} or not isinstance(value[CATEGORY],dict) or not value[CATEGORY] or not set(value[CATEGORY]).issubset(CONFIG_KEYS):
            raise ValueError('Only current turbo control/CPU speed keys may change')
        commands=[]
        for key,item in value[CATEGORY].items():
            if not isinstance(item,str) or not 1<=len(item)<=64 or any(ord(c)<32 or ord(c)>126 for c in item):raise ValueError('Config values must be exact bounded printable firmware strings')
            commands.append('configs/'+quote(CATEGORY,safe='')+'/'+quote(key,safe='')+'?value='+quote(item,safe=''))
        result=None
        for route in commands:
            result=self.client.put(route);self.stats['put_config_requests']+=1
            self.journal('bodyless_config_put',route=route)
        return result
    def request(self,method,route,data=None,content_type=None):
        if method=='POST' and route=='runners:run_prg':
            if content_type!='application/octet-stream' or not isinstance(data,bytes):raise ValueError('PRG launch requires exact immutable reviewed bytes')
            path=self.paths.get(sha(data))
            if path is None:raise ValueError('Unknown/stale PRG bytes are not registered for owned file launch')
            target='runners:run_prg?file='+quote(path,safe='')
            result=self.client.put(target);self.stats['put_prg_launches']+=1
            self.journal('owned_file_prg_put',sha256=sha(data),path=path)
            return result
        match=re.fullmatch(r'machine:writemem\?address=([0-9a-fA-F]{1,4})',route)
        if method!='POST' or not match or content_type!='application/octet-stream' or not isinstance(data,bytes) or not 1<=len(data)<=0x4000:
            raise ValueError('Unknown request/body is not permitted by the attachment-free adapter')
        address=int(match[1],16);end=address+len(data)
        windows=[(0x8000,0xc000),(0x6004,0x6005),(0x6006,0x6009),(0x600b,0x6012),self.diag]
        if not any(start<=address and end<=stop for start,stop in windows):raise ValueError('Memory write escapes reviewed staging/descriptor/mailbox ranges')
        deadline=self.clock()+self.write_seconds
        result=None
        for offset in range(0,len(data),128):
            if self.clock()>=deadline:raise TimeoutError('Bounded inline memory staging upload exceeded deadline; no retry')
            block=data[offset:offset+128]
            target=f'machine:writemem?address={address+offset:X}&data='+block.hex().upper()
            result=self.client.put(target);self.stats['put_memory_requests']+=1
            if self.clock()>=deadline:raise TimeoutError('Bounded inline memory upload completed after deadline; no GO/retry')
        self.journal('inline_memory_put_complete',address=address,bytes=len(data),chunks=(len(data)+127)//128)
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',action='store_true',required=True,help='Explicit owned FTP staging only; never executes C64')
    for name in ('host','run_id','output','recovery','recovery_sha256','native','native_sha256'):parser.add_argument('--'+name.replace('_','-'),required=True)
    args=parser.parse_args()
    output=Path(args.output).resolve()
    if not output.is_relative_to((PROJECT/'agentworking/runs').resolve()):parser.error('Evidence must remain in this project agentworking/runs')
    def connect():
        ftp=ftplib.FTP()
        try:ftp.connect(args.host,21,timeout=20);ftp.login('anonymous','anonymous@');return ftp
        except Exception:ftp.close();raise
    result=prepare_prgs(connect,{'recovery':{'path':args.recovery,'sha256':args.recovery_sha256},
                               'native':{'path':args.native,'sha256':args.native_sha256}},args.run_id,output)
    print(json.dumps({'status':result['status'],'remote_directory':result['remote_directory']}))
    return result['status']!='verified'

if __name__=='__main__':raise SystemExit(main())
