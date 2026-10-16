"""Dedicated bounded control-flow derivative; original service/data algorithms unchanged."""
import os
from pathlib import Path
from c64u_bulk_reu_recovery import Service,Journal,validate_prg,verify_backup,durable_write,dump,sha,utc,evidence_error,normalized_evidence_result
from c64u_probe import drive_media

def run_with_recovery(client, prg, output, application=None, backup_path=None, backup_manifest=None,
                      service_factory=Service, restore_attempts=2, pre_restore_evidence=None):
    """Snapshot, optional bounded application, restore+verify, then reset/resume.

    For disaster recovery pass an existing backup and its complete manifest.
    Application receives(client,run_directory); it must enforce its own bounds.
    No application is invoked until the complete backup is locally verified.
    Recovery resets execution; captured RAM is evidence, not a CPU snapshot.
    """
    validate_prg(prg)
    if restore_attempts not in (1,2,3):raise ValueError("Restoration attempts must be bounded1..3")
    if (backup_path is None)!=(backup_manifest is None):raise ValueError("Recovery needs both backup and manifest")
    if pre_restore_evidence is not None:
        pre_restore_evidence.preflight() # no device access; process/budget/input checks
    first_error=None
    def remember(error):
        nonlocal first_error
        if first_error is None:first_error=error
    verified=None
    if backup_path is not None:
        verified=verify_backup(Path(backup_path),backup_manifest) # before takeover
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    class SafeJournal(Journal):
        def __call__(self,event,**fields):
            try:return super().__call__(event,**fields)
            except BaseException as error:
                remember(error);self.errors.append(repr(error))
    journal=SafeJournal(output/"journal.jsonl")
    report={"schema":1,"status":"running","started_utc":utc(),"reu_restored":False,
            "configuration_restored":False,"reset_resumed":False,"service_prg_sha256":sha(prg),
            "limitations":["Only REU[0,4MiB) is addressed; larger capacity remainder is untouched by this helper",
            "C64 RAM and configuration are captured; prior CPU/timer/NMI execution cannot be resumed",
            "No persistent media or UCI writes; REST is development control only",
            "Application callback must enforce its own deadline and preserve media/configuration"]}
    durable_write(output/"service.prg",prg)
    turbo=machine=drives=None;takeover=False;application_started=False
    service=service_factory(client,prg,journal)
    def evidence_event(event,**fields):
        try:journal(event,**fields)
        except BaseException as error:
            remember(error)
            report["status"]="failed"
            report.setdefault("journal_errors",[]).append(evidence_error(error))
            journal.errors.append(evidence_error(error)["error"])
            if isinstance(error,(KeyboardInterrupt,SystemExit)):report["cancelled"]=True
    def stage(name):
        report["stage"]=name
        try:dump(output/"progress.json",report)
        except BaseException as error:
            remember(error)
            # Preserve the original default behavior. The opt-in evidence phase
            # adds report surfaces whose errors must never escape cleanup.
            if pre_restore_evidence is not None:
                report["status"]="failed"
                report.setdefault("progress_errors",[]).append(evidence_error(error))
                if isinstance(error,(KeyboardInterrupt,SystemExit)):report["cancelled"]=True
            journal.errors.append(evidence_error(error)["error"])
        evidence_event("stage",name=name)
    def capture_failure(name):
        try:
            client.put("machine:pause")
            durable_write(output/name,client.read(0,65536))
            journal("failure_ram_captured",file=name)
        except BaseException as error:
            remember(error)
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
            application_started=True
            report["application_result"]=application(client,output)
        report["status"]="passed"
    except BaseException as error:
        remember(error)
        report["status"]="failed";report["error"]=repr(error);journal("primary_failure",error=repr(error))
        if takeover:capture_failure("ram-failure-before-recovery.bin")
    finally:
        if verified is not None and takeover and application_started and pre_restore_evidence is not None:
            stage("retain new HD authority before restoration")
            try:
                value=pre_restore_evidence.run(client,prg,output,journal)
                report["pre_restore_evidence"]=normalized_evidence_result(value)
                if report["pre_restore_evidence"].get("status")!="passed":
                    report["status"]="failed"
                if report["pre_restore_evidence"].get("cancelled") is True:
                    report["cancelled"]=True
            except BaseException as error:
                remember(error)
                # Evidence errors must never skip the unchanged restoration block.
                report["status"]="failed"
                report["pre_restore_evidence"]={"status":"failed",**evidence_error(error)}
                if isinstance(error,(KeyboardInterrupt,SystemExit)):report["cancelled"]=True
                evidence_event("pre_restore_evidence_failed",**evidence_error(error))
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
                except BaseException as error:
                    remember(error)
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
            except BaseException as error:
                remember(error)
                report["status"]="failed";report.setdefault("cleanup_errors",[]).append(repr(error))
                if takeover:capture_failure("ram-cleanup-failure-before-reset.bin")
        if takeover:
            # Capture before reset even when reset itself is the first failure.
            capture_failure("ram-before-final-reset.bin")
            stage("reset and resume")
            reset_ok=resume_ok=False
            try:client.put("machine:reset");reset_ok=True
            except BaseException as error:
                remember(error)
                report["status"]="failed";report.setdefault("cleanup_errors",[]).append(repr(error))
            # Resume is independent: a failed/ambiguous reset must not skip it.
            try:client.put("machine:resume");resume_ok=True
            except BaseException as error:
                remember(error)
                report["status"]="failed";report.setdefault("cleanup_errors",[]).append(repr(error))
            report["reset_resumed"]=reset_ok and resume_ok
        report["finished_utc"]=utc();stage("finished")
        if journal.errors:
            report["status"]="failed";report["evidence_errors"]=journal.errors
        if first_error is not None:
            report["status"]="failed"
            if isinstance(first_error,(KeyboardInterrupt,SystemExit)):report["cancelled"]=True
        try:dump(output/"result.json",report)
        except BaseException as error:
            remember(error)
            report["status"]="failed";report.setdefault("evidence_errors",[]).append(repr(error))
    if first_error is not None:
        first_error.dos64_recovery_report=report
        raise first_error.with_traceback(first_error.__traceback__)
    return report
