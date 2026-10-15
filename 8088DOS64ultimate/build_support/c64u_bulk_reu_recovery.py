"""Development-only bounded 4 MiB REU recovery; never a DOS runtime dependency.

One resident 6510 service handles every16 KiB command. No direct REU REST API,
UCI, disk files or media commands are used. Every write is sourced from a
size/hash-verified immutable bytes object loaded from a complete local backup.
Terminal owns physical invocations; importing or testing this module contacts
no device. The application callback must enforce its own execution deadline,
stay in the first4 MiB REU, and leave mounted media/configuration unchanged.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from c64u_probe import Client, drive_media

SIZE=4*1024*1024
CHUNK=0x4000
MAILBOX=0x6000
STAGING=0x8000
READY=0x11
GO=0x47
DONE=0xa5
FAIL=0xe1


def sha(value): return hashlib.sha256(value).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()
def durable_write(path, value, mode="wb"):
    with path.open(mode) as file:
        file.write(value);file.flush();os.fsync(file.fileno())
def dump(path, value): durable_write(path,(json.dumps(value,indent=2)+"\n").encode())


class Journal:
    def __init__(self, path): self.path=path;self.errors=[]
    def __call__(self, event, **fields):
        try:
            with self.path.open("a") as file:
                file.write(json.dumps({"utc":utc(),"event":event,**fields})+"\n")
                file.flush();os.fsync(file.fileno())
        except OSError as error:
            # Evidence storage failure must NEVER prevent machine recovery.
            self.errors.append(repr(error))


def validate_prg(prg):
    if len(prg)<3 or prg[:2]!=b"\x01\x08" or 0x801+len(prg)-2>0x4000:
        raise ValueError("Recovery service must be a contiguous $0801..$3FFF PRG")


def verify_backup(path, manifest):
    if manifest.get("schema")!=1 or manifest.get("complete") is not True or manifest.get("reu_start")!=0 or manifest.get("length")!=SIZE:
        raise ValueError("Backup manifest is incomplete or has the wrong REU scope")
    data=path.read_bytes()
    if len(data)!=SIZE or sha(data)!=manifest.get("sha256"):
        raise ValueError("Backup size/hash mismatch: restoration is forbidden")
    return data                       # immutable, held for entire restoration


class Service:
    def __init__(self, client, prg, journal=lambda *a,**k:None,
                 clock=time.monotonic, sleep=time.sleep, command_seconds=12):
        validate_prg(prg)
        self.client=client;self.prg=prg;self.journal=journal
        self.clock=clock;self.sleep=sleep;self.command_seconds=command_seconds
        self.sequence=0
    def write(self, address, data):
        self.client.request("POST",f"machine:writemem?address={address:X}",data,"application/octet-stream")
    def mailbox(self):
        value=self.client.read(MAILBOX,32)
        if len(value)!=32 or value[:4]!=b"DRS1":raise ValueError("Service mailbox identity mismatch")
        return value
    def check_code(self):
        if self.client.read(0x801,len(self.prg)-2)!=self.prg[2:]:
            raise ValueError("Captured service executable differs from uploaded PRG")
    def load(self):
        self.client.put("machine:pause")
        self.write(MAILBOX+4,b"\0")
        self.client.request("POST","runners:run_prg",self.prg,"application/octet-stream")
        self.client.put("machine:resume")
        end=self.clock()+self.command_seconds
        while self.clock()<end:
            raw=self.client.read(MAILBOX,32)
            if raw[:4]==b"DRS1" and raw[4]==READY and raw[9:11]==b"\0\0":
                self.sequence=0;self.check_code();self.journal("service_loaded",prg_sha256=sha(self.prg));return
            self.sleep(0.02)
        raise TimeoutError("REU service did not initialize within deadline")
    def command(self, direction, address, count, payload=None):
        if direction not in (0,1) or not 1<=count<=CHUNK or not 0<=address<SIZE or address+count>SIZE or (address&0xffff)+count>0x10000:
            raise ValueError("Invalid bounded service command")
        if direction==0 and (not isinstance(payload,bytes) or len(payload)!=count):
            raise ValueError("Restoration command requires exact immutable bytes")
        if direction==1 and payload is not None:raise ValueError("Snapshot command cannot carry write payload")
        self.client.put("machine:pause")
        old=self.mailbox()
        if old[4] not in (READY,DONE,FAIL) or int.from_bytes(old[9:11],"little")!=self.sequence:
            raise ValueError("Service is busy or acknowledgement has diverged")
        sequence=(self.sequence+1)&0xffff
        body=bytes([direction])+sequence.to_bytes(2,"little")
        tail=address.to_bytes(3,"little")+count.to_bytes(2,"little")+(sequence^0xffff).to_bytes(2,"little")
        if direction==0:
            self.write(STAGING,payload)
            if self.client.read(STAGING,count)!=payload:raise ValueError("Restore staging readback mismatch before GO")
        self.write(MAILBOX+6,body);self.write(MAILBOX+11,tail)
        frozen=self.mailbox()
        if frozen[6:9]!=body or frozen[11:18]!=tail or frozen[9:11]!=old[9:11]:
            raise ValueError("Descriptor readback mismatch before GO")
        self.journal("command_prepared",sequence=sequence,direction=direction,address=address,length=count,
                     payload_sha256=sha(payload) if payload is not None else None)
        self.write(MAILBOX+4,bytes([GO]))        # commit AFTER descriptor + staging
        if self.client.read(MAILBOX+4,1)!=bytes([GO]):raise ValueError("GO publication readback mismatch")
        self.client.put("machine:resume")
        end=self.clock()+self.command_seconds
        while self.clock()<end:
            raw=self.mailbox()
            if raw[4] in (DONE,FAIL):
                if int.from_bytes(raw[9:11],"little")!=sequence:
                    raise ValueError("Stale or rejected command acknowledgement")
                self.sequence=sequence
                self.journal("command_ack",sequence=sequence,state=raw[4],error=raw[5],reu_error=raw[18],reu_status=raw[19])
                if raw[4]!=DONE or raw[5]:raise RuntimeError(f"Native REU command failed: {raw.hex()}")
                if direction==1:
                    block=self.client.read(STAGING,count)
                    if not isinstance(block,bytes) or len(block)!=count:
                        raise ValueError(f"Snapshot staging read length mismatch: expected {count} bytes")
                    return block
                return None
            self.sleep(0.02)
        raise TimeoutError("REU command did not acknowledge within deadline; sequence is unresolved")
    def snapshot(self, path, phase_seconds=600):
        deadline=self.clock()+phase_seconds
        with path.open("xb") as file:
            for address in range(0,SIZE,CHUNK):
                if self.clock()>=deadline:raise TimeoutError("Whole REU snapshot exceeded phase deadline")
                file.write(self.command(1,address,CHUNK))
                file.flush();os.fsync(file.fileno())
        self.check_code()
        data=path.read_bytes()
        if len(data)!=SIZE:raise ValueError("Incomplete whole REU snapshot")
        os.chmod(path,0o444)
        manifest={"schema":1,"complete":True,"reu_start":0,"length":SIZE,"sha256":sha(data),
                  "service_prg_sha256":sha(self.prg),"created_utc":utc()}
        dump(path.with_suffix(".json"),manifest)
        self.journal("backup_complete",**manifest)
        return manifest
    def restore(self, data, phase_seconds=600):
        if not isinstance(data,bytes) or len(data)!=SIZE:raise ValueError("Restoration requires verified whole immutable backup")
        deadline=self.clock()+phase_seconds
        for address in range(0,SIZE,CHUNK):
            if self.clock()>=deadline:raise TimeoutError("Whole REU restoration exceeded phase deadline")
            self.command(0,address,CHUNK,data[address:address+CHUNK])
        self.check_code()
    def compare(self, data, output, phase_seconds=600):
        if not isinstance(data,bytes) or len(data)!=SIZE:raise ValueError("Comparison requires whole immutable backup")
        deadline=self.clock()+phase_seconds
        digest=hashlib.sha256()
        with output.open("xb") as file:
            for address in range(0,SIZE,CHUNK):
                if self.clock()>=deadline:raise TimeoutError("REU readback exceeded phase deadline")
                block=self.command(1,address,CHUNK)
                if not isinstance(block,bytes) or len(block)!=CHUNK:
                    raise ValueError(f"Readback staging read length mismatch at ${address:06X}")
                file.write(block);digest.update(block)
                expected=data[address:address+CHUNK]
                if block!=expected:
                    file.flush();os.fsync(file.fileno())
                    first=next(i for i,(x,y) in enumerate(zip(block,expected)) if x!=y)
                    raise ValueError(f"Restored REU first differs at ${address+first:06X}")
            file.flush();os.fsync(file.fileno())
        self.check_code()
        if digest.hexdigest()!=sha(data):raise ValueError("Whole REU readback digest mismatch")
        self.journal("restore_verified",length=SIZE,sha256=digest.hexdigest())
        return digest.hexdigest()


def run_with_recovery(client, prg, output, application=None, backup_path=None, backup_manifest=None,
                      service_factory=Service, restore_attempts=2):
    """Snapshot, optional bounded application, restore+verify, then reset/resume.

    For disaster recovery pass an existing backup and its complete manifest.
    Application receives(client,run_directory); it must enforce its own bounds.
    No application is invoked until the complete backup is locally verified.
    Recovery resets execution; captured RAM is evidence, not a CPU snapshot.
    """
    validate_prg(prg)
    if restore_attempts not in (1,2,3):raise ValueError("Restoration attempts must be bounded1..3")
    if (backup_path is None)!=(backup_manifest is None):raise ValueError("Recovery needs both backup and manifest")
    verified=None
    if backup_path is not None:
        verified=verify_backup(Path(backup_path),backup_manifest) # before takeover
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    journal=Journal(output/"journal.jsonl")
    report={"schema":1,"status":"running","started_utc":utc(),"reu_restored":False,
            "configuration_restored":False,"reset_resumed":False,"service_prg_sha256":sha(prg),
            "limitations":["Only REU[0,4MiB) is addressed; larger capacity remainder is untouched by this helper",
            "C64 RAM and configuration are captured; prior CPU/timer/NMI execution cannot be resumed",
            "No persistent media or UCI writes; REST is development control only",
            "Application callback must enforce its own deadline and preserve media/configuration"]}
    durable_write(output/"service.prg",prg)
    turbo=machine=drives=None;takeover=False
    service=service_factory(client,prg,journal)
    def stage(name):
        report["stage"]=name
        try:dump(output/"progress.json",report)
        except OSError as error:journal.errors.append(repr(error))
        journal("stage",name=name)
    def capture_failure(name):
        try:
            client.put("machine:pause")
            durable_write(output/name,client.read(0,65536))
            journal("failure_ram_captured",file=name)
        except Exception as error:
            report["status"]="failed"
            report.setdefault("failure_capture_errors",[]).append(repr(error));journal("failure_ram_capture_failed",error=repr(error))
    try:
        stage("inventory")
        dump(output/"info.json",client.get("info"))
        turbo=client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
        machine=client.get("configs/C64%20and%20Cartridge%20Settings")
        drives=client.get("drives")
        dump(output/"turbo-before.json",turbo);dump(output/"machine-before.json",machine);dump(output/"drives-before.json",drives)
        settings=machine["C64 and Cartridge Settings"]
        size=settings["REU Size"].split()
        if settings["RAM Expansion Unit"]!="Enabled" or len(size)!=2 or size[1]!="MB" or int(size[0])<4:
            raise ValueError("An already-enabled REU of at least4 MiB is required")
        takeover=True;client.put("machine:pause")
        durable_write(output/"ram-before.bin",client.read(0,65536))
        if verified is None:
            stage("snapshot")
            service.load()
            backup_path=output/"reu-before.bin"
            backup_manifest=service.snapshot(backup_path)
            verified=verify_backup(backup_path,backup_manifest)
        else:
            durable_write(output/"reu-before.bin",verified);os.chmod(output/"reu-before.bin",0o444)
            dump(output/"reu-before.json",backup_manifest)
        report["backup"]={"path":str(Path(backup_path).resolve()),**backup_manifest}
        stage("backup verified")
        if application is not None:
            if journal.errors:raise OSError("Application launch requires a healthy recovery journal")
            stage("application")
            report["application_result"]=application(client,output)
        report["status"]="passed"
    except Exception as error:
        report["status"]="failed";report["error"]=repr(error);journal("primary_failure",error=repr(error))
        if takeover:capture_failure("ram-failure-before-recovery.bin")
    finally:
        if verified is not None and takeover:
            stage("restore and full readback")
            for attempt in range(1,restore_attempts+1):
                try:
                    # Recheck the immutable local source before EVERY write pass.
                    current=verify_backup(Path(backup_path),backup_manifest)
                    if current!=verified:raise ValueError("Backup changed since initial verification")
                    if client.get("configs/C64%20and%20Cartridge%20Settings")!=machine:
                        raise ValueError("Machine/REU configuration changed before restoration")
                    service.load()
                    service.restore(verified)
                    digest=service.compare(verified,output/f"reu-after-{attempt}.bin")
                    report["reu_restored"]=True;report["restore_attempts"]=attempt;report["restored_sha256"]=digest
                    break
                except Exception as error:
                    report.setdefault("restore_errors",[]).append(repr(error));journal("restore_failure",attempt=attempt,error=repr(error))
                    capture_failure(f"ram-restore-failure-{attempt}-before-reset.bin")
            if not report["reu_restored"]:report["status"]="failed"
        if turbo is not None:
            stage("configuration recovery")
            try:
                # Helper changes no machine/media settings. Restore turbo, and
                # explicitly reject unexpected machine/media changes.
                client.configs({"U64 Specific Settings":{"Turbo Control":turbo["Turbo Control"],"CPU Speed":turbo["CPU Speed"]}})
                after=client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
                machine_after=client.get("configs/C64%20and%20Cartridge%20Settings")
                drives_after=client.get("drives")
                dump(output/"turbo-after.json",after);dump(output/"machine-after.json",machine_after);dump(output/"drives-after.json",drives_after)
                if after!=turbo or machine_after!=machine or drive_media(drives_after)!=drive_media(drives):
                    raise ValueError("Configuration/media differs; helper cannot reconstruct unexpected mounted-media changes")
                report["configuration_restored"]=True
            except Exception as error:
                report["status"]="failed";report.setdefault("cleanup_errors",[]).append(repr(error))
                if takeover:capture_failure("ram-cleanup-failure-before-reset.bin")
        if takeover:
            # Capture before reset even when reset itself is the first failure.
            capture_failure("ram-before-final-reset.bin")
            stage("reset and resume")
            reset_ok=resume_ok=False
            try:client.put("machine:reset");reset_ok=True
            except Exception as error:
                report["status"]="failed";report.setdefault("cleanup_errors",[]).append(repr(error))
            # Resume is independent: a failed/ambiguous reset must not skip it.
            try:client.put("machine:resume");resume_ok=True
            except Exception as error:
                report["status"]="failed";report.setdefault("cleanup_errors",[]).append(repr(error))
            report["reset_resumed"]=reset_ok and resume_ok
        report["finished_utc"]=utc();stage("finished")
        if journal.errors:
            report["status"]="failed";report["evidence_errors"]=journal.errors
        try:dump(output/"result.json",report)
        except OSError as error:
            report["status"]="failed";report.setdefault("evidence_errors",[]).append(repr(error))
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host",required=True)
    parser.add_argument("--service",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--backup",type=Path,help="Existing complete backup for disaster restoration")
    parser.add_argument("--manifest",type=Path,help="Matching complete backup manifest")
    args=parser.parse_args()
    if bool(args.backup)!=bool(args.manifest):parser.error("--backup and --manifest are required together")
    manifest=json.loads(args.manifest.read_text()) if args.manifest else None
    result=run_with_recovery(Client(args.host),args.service.read_bytes(),args.output,
                            backup_path=args.backup,backup_manifest=manifest)
    print(json.dumps({k:result[k] for k in ("status","reu_restored","configuration_restored","reset_resumed")}))
    raise SystemExit(result["status"]!="passed")
