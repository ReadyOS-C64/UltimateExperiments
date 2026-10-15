"""Terminal-owned physical cache test with verified REU/configuration recovery."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error


def sha(data):
    return hashlib.sha256(data).hexdigest()


def restore_image(base, backup):
    if len(base) < 3 or int.from_bytes(base[:2], "little") != 0x801:
        raise ValueError("Unexpected restore PRG header")
    if len(backup) != 2048 or 0x801+len(base)-2 > 0x4000:
        raise ValueError("Invalid backup size or restore executable range")
    return base + bytes(0x6000-(0x801+len(base)-2)) + backup


def validate_probe(data, mailbox):
    expected=bytes((i & 255) ^ (i>>8) ^ 0xa7 for i in range(1536))
    if data != expected:
        raise ValueError("Physical cache readback does not match all 1536 bytes")
    if len(mailbox)!=8 or mailbox[0]!=1 or mailbox[1]!=0xa5 or mailbox[4]!=0:
        raise ValueError("Physical probe mailbox failed")


def drive_media(value):
    # Reset can change a SoftIEC last-error string. Compare actual media/settings.
    return [{name:{k:v for k,v in item.items() if k!="last_error"} for name,item in d.items()}
            for d in value["drives"]]


def speed_option(values, speed):
    matches=[v for v in values if str(v).strip()==str(speed)]
    if len(matches)!=1:raise ValueError(f"No unique firmware speed option for {speed}")
    return matches[0]


class Client:
    def __init__(self, host):
        self.url=f"http://{host}/v1/"

    def request(self, method, route, data=None, content_type=None):
        headers={"Content-Type":content_type} if content_type else {}
        req=urllib.request.Request(self.url+route, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=5) as response:
                raw=response.read()
                if response.headers.get("Content-Type","").startswith("application/json"):
                    value=json.loads(raw)
                    if value.get("errors"):
                        raise RuntimeError(f"{route}: {value['errors']}")
                    return value
                return raw
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{method} {route}: HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc

    def get(self, route):
        return self.request("GET",route)

    def put(self, route):
        return self.request("PUT",route)

    def configs(self, value):
        return self.request("POST","configs",json.dumps(value).encode(),"application/json")

    def read(self, address, length):
        data=self.get(f"machine:readmem?address={address:X}&length={length}")
        if not isinstance(data,bytes) or len(data)!=length:
            raise ValueError(f"Invalid memory read length at {address:x}")
        return data

    def run(self, prg, mailbox_address, executable_length=None):
        self.put("machine:pause")
        self.request("POST",f"machine:writemem?address={mailbox_address+1:X}",b"\0","application/octet-stream")
        self.request("POST","runners:run_prg",prg,"application/octet-stream")
        self.put("machine:resume")
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            mailbox=self.read(mailbox_address,8)
            if mailbox[1] in (0xa5,0xe1):
                if mailbox[1]!=0xa5 or mailbox[4]!=0:
                    raise RuntimeError(f"Target reported {mailbox.hex()}")
                payload=prg[2:2+executable_length] if executable_length is not None else prg[2:]
                if self.read(0x801,len(payload))!=payload:
                    raise ValueError("Physical captured executable differs from uploaded PRG")
                return mailbox
            time.sleep(0.05)
        raise TimeoutError("Native probe did not complete within 12 seconds")


def run_matrix(client, project, out):
    out.mkdir(parents=True,exist_ok=True)
    def save(name, value):
        path=out/name
        path.write_bytes(value) if isinstance(value,bytes) else path.write_text(json.dumps(value,indent=2)+"\n")
    report={"schema":1,"status":"running","started_utc":datetime.now(timezone.utc).isoformat(),
            "pid":os.getpid(),"speeds":[],"reu_restored":False,"configuration_restored":False,
            "limitations":["Integrity at selected manual turbo settings; no elapsed CPU/DMA timing",
                            "C64 RAM captured for recovery; prior program execution is not resumed",
                            "No disk/UCI writes; runners upload PRGs directly to volatile RAM"]}
    save("pid.json",{"pid":os.getpid()})
    def progress(stage):
        report["stage"]=stage;save("progress.json",report)
    turbo=None;backup=None;original_machine=None;original_drives=None;ran_program=False
    backup_prg=(project/"build/dos64-backup.prg").read_bytes()
    restore_base=(project/"build/dos64-restore.prg").read_bytes()
    probe=(project/"build/dos64-cache-probe.prg").read_bytes()
    restore_image(restore_base,bytes(2048))  # Validate recovery inputs before hardware actions.
    labels={}
    for line in (project/"build/dos64-cache-probe.labels").read_text().splitlines():
        fields=line.split()
        if len(fields)==3 and fields[0]=="al":labels[fields[2].lstrip(".")]=int(fields[1],16)
    mailbox=labels["dos64_mailbox"]
    report["artifacts"]={"backup_prg_sha256":sha(backup_prg),"restore_base_sha256":sha(restore_base),"probe_prg_sha256":sha(probe)}
    try:
        progress("inventory")
        report["device"]=client.get("info");save("info.json",report["device"])
        turbo=client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
        original_machine=client.get("configs/C64%20and%20Cartridge%20Settings")
        original_drives=client.get("drives")
        controls=client.get("configs/U64%20Specific%20Settings/Turbo%20Control")["U64 Specific Settings"]["Turbo Control"]["values"]
        speeds=client.get("configs/U64%20Specific%20Settings/CPU%20Speed")["U64 Specific Settings"]["CPU Speed"]["values"]
        report["firmware_options"]={"turbo":controls,"speed":speeds}
        if "Manual" not in controls:raise ValueError("Firmware does not offer Manual turbo control")
        save("turbo-before.json",turbo);save("machine-before.json",original_machine);save("drives-before.json",original_drives)
        if original_machine["C64 and Cartridge Settings"]["RAM Expansion Unit"]!="Enabled":
            raise ValueError("REU must already be enabled")
        size=original_machine["C64 and Cartridge Settings"]["REU Size"].split()
        if len(size)!=2 or size[1]!="MB" or int(size[0])<4:
            raise ValueError("Hardware REU capacity must be at least 4 MiB")
        progress("RAM recovery capture")
        client.put("machine:pause")
        save("ram-before.bin",client.read(0,65536))
        progress("backup REU envelope")
        ran_program=True
        client.run(backup_prg,mailbox)
        backup=client.read(0x6000,2048)
        save("reu-before.bin",backup)
        report["reu_before_sha256"]=sha(backup)
        for speed in (1,16,64):
            progress(f"cache probe {speed} MHz")
            option=speed_option(speeds,speed)
            client.configs({"U64 Specific Settings":{"Turbo Control":"Manual","CPU Speed":option}})
            active=client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
            if active["Turbo Control"]!="Manual" or str(active["CPU Speed"]).strip()!=str(speed):
                raise ValueError("Requested manual turbo setting was not applied")
            result=client.run(probe,mailbox)
            data=client.read(0x6000,1536)
            validate_probe(data,result)
            save(f"readback-{speed}.bin",data);save(f"mailbox-{speed}.bin",result)
            save(f"ram-{speed}.bin",client.read(0,65536))
            report["speeds"].append({"mhz_setting":speed,"firmware_speed_value":option,"turbo_control":"Manual","result":"pass",
                                     "readback_sha256":sha(data),"mailbox_hex":result.hex()})
        report["status"]="passed"
    except Exception as exc:
        report["status"]="failed";report["error"]=repr(exc)
    finally:
        if backup is not None:
            progress("restore and verify REU envelope")
            restoration=restore_image(restore_base,backup);save("restore-owned.prg",restoration)
            for attempt in range(1,4):
                try:
                    client.run(restoration,mailbox,len(restore_base)-2)
                    client.run(backup_prg,mailbox)
                    restored=client.read(0x6000,2048);save("reu-after.bin",restored)
                    if restored!=backup:raise ValueError("Restored REU differs from saved envelope")
                    report["reu_restored"]=True;report["restore_attempts"]=attempt
                    break
                except Exception as exc:
                    report.setdefault("restore_errors",[]).append(repr(exc))
            if not report["reu_restored"]:report["status"]="failed"
        if turbo is not None:
            progress("restore configuration")
            try:
                client.configs({"U64 Specific Settings":{"Turbo Control":turbo["Turbo Control"],"CPU Speed":turbo["CPU Speed"]}})
                after=client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
                machine=client.get("configs/C64%20and%20Cartridge%20Settings")
                drives=client.get("drives")
                save("turbo-after.json",after);save("machine-after.json",machine);save("drives-after.json",drives)
                if after!=turbo or machine!=original_machine or drive_media(drives)!=drive_media(original_drives):
                    raise ValueError("Prior turbo/machine/media configuration differs after test")
                report["configuration_restored"]=True
                if ran_program:client.put("machine:reset")
                client.put("machine:resume")
            except Exception as exc:
                report["status"]="failed";report["configuration_restore_error"]=repr(exc)
        report["finished_utc"]=datetime.now(timezone.utc).isoformat()
        progress("finished");save("result.json",report)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--host",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    report=run_matrix(Client(args.host),project,args.output.resolve())
    print(json.dumps({k:report[k] for k in ("status","speeds","reu_restored","configuration_restored")}))
    raise SystemExit(report["status"]!="passed")
