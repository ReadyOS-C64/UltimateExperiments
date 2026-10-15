"""Bounded native DOS development lane. Prepared without hardware execution.

Requires a reviewed runtime ABI and a genuinely verified media-fixture record.
Development control only; all scripted input goes through native keyboard enqueue.
"""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from c64u_probe import Client,speed_option
from c64u_bulk_reu_recovery import Service,Journal,run_with_recovery,durable_write,dump,CHUNK
from c64u_native_application_support import verified_media,patch_config,decode_screen,Builtins,sha,SOURCE_SHA

# ABI confirmed by the frozen native startup source; exact PRG/map/labels are pinned per run.
FIELDS={'size':142,'enabled':4,'path_length':7,'expected_crc':10,'path':14,'path_capacity':128}
DIAG_SIZE=19
STAGE_IMPORT=2
STAGE_RUN=4
STAGE_PAUSED=5
STAGE_FAILED=0xe1


def resident_from_map(path):
    import re
    text=Path(path).read_text()
    if 'Segment list:' not in text or 'Exports list' not in text:raise ValueError('Invalid runtime linker map')
    block=text.split('Segment list:',1)[1].split('Exports list',1)[0]
    keep={'BASIC','CODE','RODATA','DEVICECODE','TESTCODE'}
    segments=[]
    for line in block.splitlines():
        match=re.fullmatch(r'([A-Z]+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]+',line)
        if match and match[1] in keep:
            start,end,length=(int(match[i],16) for i in (2,3,4))
            if not length or end-start+1!=length:raise ValueError('Invalid resident segment span')
            segments.append({'name':match[1],'start':start,'length':length})
    if not {'BASIC','CODE','RODATA','DEVICECODE'}.issubset({x['name'] for x in segments}):raise ValueError('Required resident source segments are missing')
    return segments


def pinned_hashes(value):
    import re
    if isinstance(value,str):return {value} if re.fullmatch(r'[0-9a-f]{64}',value) else set()
    if isinstance(value,dict):return set().union(*(pinned_hashes(v) for v in value.values())) if value else set()
    if isinstance(value,list):return set().union(*(pinned_hashes(v) for v in value)) if value else set()
    return set()


def labels_from(path):
    labels={}
    for line in Path(path).read_text().splitlines():
        words=line.split()
        if len(words)==3 and words[0]=='al':labels[words[2].lstrip('.')]=int(words[1],16)
    for required in ('dos64_native_config','dos64_native_config_end','dos64_native_diag','dos64_native_diag_end',
                     'dos64_cpu_instructions','dos64_bios_waiting'):
        if required not in labels:raise ValueError(f'Missing reviewed runtime symbol: {required}')
    if labels['dos64_native_config_end']-labels['dos64_native_config']!=FIELDS['size'] or labels['dos64_native_diag_end']-labels['dos64_native_diag']!=DIAG_SIZE:
        raise ValueError('Native ABI size differs from reviewed runner layout')
    return labels


class Application:
    def __init__(self,prg,labels,media,source,service_prg,expected_prg_sha,seconds=180,
                 clock=time.monotonic,sleep=time.sleep,resident_segments=None,build_identity=None):
        if sha(prg)!=expected_prg_sha:raise ValueError('Runtime PRG differs from reviewed build identity')
        if not 10<=seconds<=180:raise ValueError('Application deadline must be bounded10..180 seconds')
        data,path=verified_media(media,source)
        config_offset=labels['dos64_native_config']-0x801+2
        if int.from_bytes(prg[config_offset+8:config_offset+10],'little')!=0xdf1c:
            raise ValueError('Reviewed first physical fixture requires the original compiled UCI base DF1C')
        patched,patch=patch_config(prg,labels['dos64_native_config'],FIELDS,path,media['source_crc32'])
        self.prg=patched;self.labels=labels;self.media=media;self.source=Path(source);self.data=data
        self.service_prg=service_prg;self.patch=patch;self.seconds=seconds;self.clock=clock;self.sleep=sleep
        self.base=labels['dos64_native_diag'];self.script=Builtins(data)
        self.resident_segments=resident_segments or []
        self.build_identity=build_identity or {'scope':'mocked runner fixture only; no hardware build identity supplied'}
        self.observations=[];self.client=None;self.output=None;self.journal=None;self.deadline=None;self.app_upload_started=False
    def bound(self):
        if self.clock()>=self.deadline:raise TimeoutError('Native application exceeded its bounded execution/evidence deadline')
    def write(self,address,data):
        self.client.request('POST',f'machine:writemem?address={address:X}',data,'application/octet-stream')
    def diag(self):
        value=self.client.read(self.base,DIAG_SIZE)
        if not isinstance(value,bytes) or len(value)!=DIAG_SIZE:raise ValueError('Truncated native diagnostic mailbox')
        return value
    def command(self,command,key=None,address=None,count=None):
        self.bound();self.client.put('machine:pause')
        before=self.diag()
        if before[3]!=0:raise ValueError('Native command already outstanding')
        if before[0]==STAGE_FAILED:raise RuntimeError(f'Native stage failed: {before.hex()}')
        self.write(self.base+4,b'\0')          # invalidate prior result BEFORE GO
        if key is not None:self.write(self.base+5,key.to_bytes(2,'little'))
        if address is not None:
            if count is None or not 1<=count<=2048 or not 0<=address<0x100000 or address+count>0x100000 or (address&0xffff)+count>0x10000:
                raise ValueError('Invalid paused read-only native dump span')
            self.write(self.base+14,address.to_bytes(3,'little')+count.to_bytes(2,'little'))
        self.write(self.base+3,bytes([command])) # command published LAST while paused
        published=self.diag()
        if published[3]!=command or published[4]!=0:raise ValueError('Native command publication readback mismatch')
        if key is not None and published[5:7]!=key.to_bytes(2,'little'):raise ValueError('Native key body readback mismatch')
        if address is not None and published[14:19]!=address.to_bytes(3,'little')+count.to_bytes(2,'little'):
            raise ValueError('Native read body readback mismatch')
        self.journal('native_command_go',command=command,key=key,address=address,count=count)
        self.client.put('machine:resume')
        end=min(self.deadline,self.clock()+12)
        while self.clock()<end:
            done=self.diag()
            if done[0]==STAGE_FAILED:raise RuntimeError(f'Native failure during command: {done.hex()}')
            if done[3]==0 and done[4] in (0xa5,0xe1):
                self.journal('native_command_ack',command=command,mailbox_hex=done.hex())
                if done[4]!=0xa5:raise RuntimeError(f'Native command rejected: {done.hex()}')
                return done
            self.sleep(0.02)
        raise TimeoutError('Native command acknowledgement deadline; command will not be reissued')
    def read_paused(self,address,count):
        result=bytearray()
        while count:
            self.bound();n=min(count,2048,0x10000-(address&0xffff))
            ack=self.command(4,address=address,count=n)
            if ack[0]!=STAGE_PAUSED:raise ValueError('Read command escaped coherent paused phase')
            block=self.client.read(0xc100,n)
            if not isinstance(block,bytes) or len(block)!=n:raise ValueError('Truncated native read-only staging data')
            result.extend(block);address+=n;count-=n
        return bytes(result)
    def screen(self):
        ack=self.command(2)
        if ack[0]!=STAGE_PAUSED:raise ValueError('SNAPSHOT did not publish coherent paused phase')
        bda=self.read_paused(0x400,256)
        cols=int.from_bytes(bda[0x4a:0x4c],'little');offset=int.from_bytes(bda[0x4e:0x50],'little')
        if cols not in (40,80) or offset+cols*25*2>0x4000:raise ValueError('Active video span is invalid')
        video=self.read_paused(0xb8000+offset,cols*25*2)
        screen=decode_screen(bda,video)
        count=int.from_bytes(self.client.read(self.labels['dos64_cpu_instructions'],4),'little')
        screen.update(guest_instructions=count,coherent=True,host_elapsed_seconds=self.clock()-self.started)
        self.journal('coherent_screen',guest_instructions=count,sha256=sha(video),stage=self.script.stage)
        return screen
    def verify_resident(self,ram):
        proofs=[]
        for segment in self.resident_segments:
            start=segment['start'];length=segment['length'];offset=start-0x801+2
            if offset<2 or offset+length>len(self.prg):raise ValueError('Resident segment outside source PRG')
            expected=self.prg[offset:offset+length];actual=ram[start:start+length]
            proof={**segment,'source_sha256':sha(expected),'captured_sha256':sha(actual),'matches':actual==expected}
            proofs.append(proof)
            if actual!=expected:
                first=next(i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y)
                proof['first_difference_address']=start+first
        dump(self.output/'captured-resident-identity.json',proofs)
        if any(not p['matches'] for p in proofs):raise ValueError('Captured resident executable differs from uploaded reviewed code')
        return proofs
    def capture_ram(self,name):
        self.client.put('machine:pause')
        ram=self.client.read(0,65536)
        if len(ram)!=65536:raise ValueError('Truncated full C64 RAM evidence')
        durable_write(self.output/name,ram)
        return sha(ram)
    def extract_reu(self,address,length,name):
        service=self.evidence_service
        result=bytearray()
        offset=0
        while offset<length:
            self.bound();n=min(CHUNK,length-offset,0x10000-((address+offset)&0xffff))
            block=service.command(1,address+offset,n)
            if len(block)!=n:raise ValueError('Truncated final REU evidence')
            result.extend(block);offset+=n
        durable_write(self.output/name,bytes(result))
        return bytes(result)
    def preflight(self):
        machine=self.client.get('configs/C64%20and%20Cartridge%20Settings')
        settings=machine['C64 and Cartridge Settings']
        record={'actual_machine_settings':machine,'selected_native_uci_base':'DF1C',
                'base_validation':'Real native UCI start validates base+1 masked7F=49 before any command/control write; REST readmem is not treated as I/O',
                'machine_settings_changed':False,'status':'checking'}
        dump(self.output/'application-preflight.json',record)
        if settings.get('Command Interface')!='Enabled':
            record['status']='failed';record['error']='Actual Command Interface is disabled or unavailable'
        else:
            size=str(settings.get('REU Size','')).split()
            if settings.get('RAM Expansion Unit')!='Enabled' or len(size)!=2 or size[1]!='MB' or not size[0].isdigit() or int(size[0])<4:
                record['status']='failed';record['error']='Actual REU must already be enabled with at least4MiB'
            else:record['status']='passed'
        dump(self.output/'application-preflight.json',record)
        if record['status']!='passed':raise ValueError(record['error'])
        return record
    def __call__(self,client,output):
        self.client=client;self.output=Path(output);self.journal=Journal(self.output/'application-journal.jsonl')
        self.started=self.clock();self.deadline=self.started+self.seconds
        report={'status':'running','physical_script':'VER then DIR /P','coherent_final_guest':False,
                'limitations':['Explicit native test mailbox enqueues real BIOS keys; physical matrix keyboard remains a separate acceptance',
                              'Guest DOS runs unchanged; no INT21 replacement or native EXE loader',
                              'Runtime target path is a read-only freshly owned disk fixture',
                              'No CPU/timer execution restoration; outer helper restores first4MiB REU and machine configuration']}
        durable_write(self.output/'native-owned.prg',self.prg)
        dump(self.output/'native-patch.json',self.patch);dump(self.output/'media-fixture-input.json',self.media)
        dump(self.output/'runtime-symbols.json',self.labels)
        dump(self.output/'runtime-build-identity.json',self.build_identity)
        source_identity={}
        for path in (Path(__file__).resolve(),Path(__file__).resolve().with_name('c64u_native_application_support.py'),
                     Path(__file__).resolve().with_name('c64u_bulk_reu_recovery.py'),
                     Path(__file__).resolve().with_name('c64u_probe.py')):
            body=path.read_bytes();source_identity[str(path)]={'sha256':sha(body),'bytes':len(body)}
            durable_write(self.output/('runner-source-'+path.name),body)
        dump(self.output/'runner-source-identities.json',source_identity)
        try:
            # Development setup only. Outer recovery has already captured prior
            # configuration and verified the complete first4MiB local backup.
            report['preflight']=self.preflight()
            options=client.get('configs/U64%20Specific%20Settings/CPU%20Speed')['U64 Specific Settings']['CPU Speed']['values']
            option=speed_option(options,64)
            client.configs({'U64 Specific Settings':{'Turbo Control':'Manual','CPU Speed':option}})
            active=client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
            if active['Turbo Control']!='Manual' or str(active['CPU Speed']).strip()!='64':raise ValueError('Manual64MHz was not applied')
            report['active_turbo']=active
            client.put('machine:pause');self.write(self.base,bytes(DIAG_SIZE))
            self.app_upload_started=True
            client.request('POST','runners:run_prg',self.prg,'application/octet-stream');client.put('machine:resume')
            prior_wait=None;last_stage=None;last_capture=self.started
            while True:
                self.bound();diag=self.diag()
                if diag[0]!=last_stage:
                    self.journal('native_stage',mailbox_hex=diag.hex());last_stage=diag[0]
                if diag[0]==STAGE_FAILED:raise RuntimeError(f'Native startup/runtime failure: {diag.hex()}')
                if diag[0]==STAGE_RUN:
                    waiting=client.read(self.labels['dos64_bios_waiting'],1)
                    counter=client.read(self.labels['dos64_cpu_instructions'],4)
                    token=(waiting,counter)
                    if (waiting==b'\x01' and token==prior_wait) or self.clock()-last_capture>=0.25:
                        # Real DOS may poll INT16 AH01 without the AH00
                        # blocking flag. Periodic coherent captures service both.
                        screen=self.screen();last_capture=self.clock();keys=self.script.observe(screen)
                        dump(self.output/'builtins-progress.json',self.script.result())
                        if self.script.stage=='done':break
                        self.command(3)
                        for key in keys:self.command(1,key=key)
                        prior_wait=None
                    else:prior_wait=token
                self.sleep(0.05)
            report['application_ram_sha256']=self.capture_ram('application-ram-before-recovery.bin')
            captured=(self.output/'application-ram-before-recovery.bin').read_bytes()
            report['resident_identity']=self.verify_resident(captured)
            durable_write(self.output/'application-mailbox-before-recovery.bin',self.diag())
            # Full640KiB and VRAM are now authoritative in REU because SNAPSHOT
            # flushed and paused the runtime. Save RAM BEFORE overwriting code.
            self.evidence_service=Service(client,self.service_prg,self.journal,clock=self.clock,sleep=self.sleep)
            self.evidence_service.load()
            guest=self.extract_reu(0,640*1024,'guest-640k-coherent.bin')
            video=self.extract_reu(0xb8000,0x4000,'cga-16k-coherent.bin')
            floppy=self.extract_reu(0x100000,368640,'floppy-import-after.bin')
            if floppy!=self.data:raise ValueError('Loaded floppy differs from every original source byte')
            report.update(status='passed',coherent_final_guest=True,guest_sha256=sha(guest),cga_sha256=sha(video),
                          floppy_sha256=sha(floppy),floppy_original_unchanged=True)
            return report
        except Exception as error:
            report.update(status='failed',error=repr(error))
            try:
                report['failure_ram_sha256']=self.capture_ram('application-failure-before-reset.bin')
                if self.app_upload_started:
                    try:report['resident_identity']=self.verify_resident((self.output/'application-failure-before-reset.bin').read_bytes())
                    except Exception as identity_error:report['failure_resident_identity_error']=repr(identity_error)
            except Exception as capture_error:report['failure_capture_error']=repr(capture_error)
            raise
        finally:
            report['script_result']=self.script.result();report['elapsed_seconds']=self.clock()-self.started
            source_error=None
            try:report['original_source_unchanged']=sha(self.source.read_bytes())==SOURCE_SHA
            except Exception as error:
                report['original_source_unchanged']=False;source_error=repr(error)
                report['final_source_read_error']=source_error
            report['journal_errors']=self.journal.errors
            late_error=not report['original_source_unchanged'] or bool(self.journal.errors)
            was_passed=report['status']=='passed'
            if late_error:report['status']='failed'
            dump(self.output/'application-result.json',report)
            # Preserve an earlier native/runtime failure. A late source read
            # failure must still make a successful application fail outward.
            if was_passed and not report['original_source_unchanged']:
                raise ValueError('Original source final verification failed: '+str(source_error))
            if was_passed and self.journal.errors:raise OSError('Native application evidence journal failed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('host','prg','labels','map','build_manifest','media_manifest','source','service','output','expected_prg_sha256'):
        parser.add_argument('--'+name.replace('_','-'),required=True)
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    out=Path(args.output).resolve()
    if not out.is_relative_to((project/'agentworking/runs').resolve()):parser.error('Output must be project-owned agentworking/runs')
    symbols=labels_from(args.labels)
    resident=resident_from_map(args.map)
    build_identity=json.loads(Path(args.build_manifest).read_text())
    pins=pinned_hashes(build_identity)
    for artifact in (args.prg,args.labels,args.map):
        if sha(Path(artifact).read_bytes()) not in pins:
            parser.error('Runtime PRG/labels/map identity is missing from the frozen build manifest: '+artifact)
    app=Application(Path(args.prg).read_bytes(),symbols,json.loads(Path(args.media_manifest).read_text()),
                    args.source,Path(args.service).read_bytes(),args.expected_prg_sha256,
                    resident_segments=resident,build_identity=build_identity)
    # Root launches through Terminal after reviewing frozen source/binary/media
    # identities. Importing this module or running mocked tests contacts no host.
    result=run_with_recovery(Client(args.host),app.service_prg,out,application=app)
    print(json.dumps({k:result[k] for k in ('status','reu_restored','configuration_restored','reset_resumed')}))
    return result['status']!='passed'

if __name__=='__main__':raise SystemExit(main())
