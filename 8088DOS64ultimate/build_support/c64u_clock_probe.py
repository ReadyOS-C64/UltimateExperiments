"""Terminal-owned CIA/VIC clock matrix; volatile PRGs only, no REU/UCI/files.

This destructively takes CIA2 timers and the RAM NMI vector. Save complete RAM
for recovery evidence, preserve machine/media/manual-speed settings, and reset/
resume in finally. It does not claim restoration of the former timer, NMI or
CPU execution state. Root must launch explicitly through the established
Terminal workflow; importing this module never contacts hardware.
"""
import argparse
from datetime import datetime, timezone
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

from c64u_probe import Client, drive_media, sha, speed_option
from clock_probe_verify import labels_from, verify_capture, verify_matrix, inspect_capture


def tool_identity(project):
    result = {'python': {'path': os.sys.executable, 'version': platform.python_version()}}
    zig_default = project / '../../zeropage-tooling/bin/zig'
    for name, variable, default, arguments in (
            ('ca65', 'DOS64_CA65', 'ca65', ['--version']),
            ('ld65', 'DOS64_LD65', 'ld65', ['--version']),
            ('zig', 'DOS64_ZIG', str(zig_default) if zig_default.is_file() else 'zig', ['version'])):
        program = os.environ.get(variable, default)
        resolved = shutil.which(program)
        if resolved is None:
            result[name] = {'requested': program, 'available': False}
            continue
        try:
            command = subprocess.run([resolved] + arguments, capture_output=True, text=True, timeout=5)
            result[name] = {'path': str(Path(resolved).resolve()),
                            'version': (command.stdout + command.stderr).strip(),
                            'exit_code': command.returncode}
        except Exception as exc:
            result[name] = {'path': resolved, 'error': repr(exc)}
    return result


def run_matrix(client, project, out):
    # Refuse to mix evidence with old runs before touching hardware.
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Clock run directory must be new or empty")
    project = Path(project)
    prg = (project / 'build/dos64-clock-probe.prg').read_bytes()
    labels_path = project / 'build/dos64-clock-probe.labels'
    map_path = project / 'build/dos64-clock-probe.map'
    map_bytes = map_path.read_bytes()
    labels = labels_from(labels_path)
    mailbox = labels['dos64_mailbox']
    if len(prg) < 3 or prg[:2] != b'\x01\x08' or 0x801 + len(prg)-2 > 0x6000:
        raise ValueError("Invalid or overlapping clock probe PRG")
    if labels.get('dos64_entry') != 0x80d or labels.get('dos64_host_clock_probe_record') != 0x6000:
        raise ValueError("Wrong clock probe linker symbols")
    out.mkdir(parents=True, exist_ok=True)
    def save(name, value):
        path = out / name
        if isinstance(value, bytes):
            path.write_bytes(value)
        else:
            path.write_text(json.dumps(value, indent=2) + '\n')
    report = {'schema': 1, 'status': 'running', 'pid': os.getpid(),
              'started_utc': datetime.now(timezone.utc).isoformat(), 'speeds': [],
              'configuration_restored': False, 'reset_resumed': False,
              'artifacts': {'probe_prg_sha256': sha(prg),
                            'probe_labels_sha256': sha(labels_path.read_bytes()),
                            'probe_map_sha256': sha(map_bytes)},
              'tools_observed_at_run': tool_identity(project),
              'limitations': ['Raw CIA phi2 ticks versus PAL raster; no CPU/XT throughput',
                              'CIA2 timer and RAM NMI takeover is followed by reset/resume',
                              'RAM capture is recovery evidence, not prior program resumption',
                              'No REU, UCI, filesystem or persistent-media writes']}
    report['source_sha256'] = {name: sha((project / name).read_bytes())
        for name in ('src/host_clock.s', 'src/host_clock_probe.s',
                     'src/host_clock_probe_boot.s', 'include/abi.inc',
                     'include/host_clock.inc', 'cfg/dos64-clock-probe.cfg',
                     'Makefile', 'build.zig', 'build_support/clock_probe_verify.py',
                     'build_support/c64u_clock_probe.py')
        if (project / name).is_file()}
    save('probe-uploaded.prg', prg)
    save('probe.labels', labels_path.read_bytes())
    save('probe.map', map_bytes)
    save('pid.json', {'pid': os.getpid()})
    def progress(stage):
        report['stage'] = stage
        save('progress.json', report)
    def failure_capture(speed):
        # Client.run raises on target FAIL or launch/readback failure. Preserve
        # native diagnostics BEFORE reset, even when that original call raised.
        evidence = {'mhz_setting': speed, 'kind': 'diagnostic-only'}
        try:
            client.put('machine:pause')
        except Exception as exc:
            evidence['pause_error'] = repr(exc)
        try:
            ram = client.read(0, 65536)
            save(f'ram-failed-{speed}.bin', ram)
            save(f'mailbox-failed-{speed}.bin', ram[mailbox:mailbox+8])
            save(f'record-failed-{speed}.bin', ram[0x6000:0x6028])
            evidence.update(inspect_capture(ram, prg, mailbox))
        except Exception as exc:
            evidence['capture_error'] = repr(exc)
        save(f'failure-{speed}.json', evidence)
        report['failure_capture'] = evidence

    turbo = machine = drives = None
    program_attempted = False
    captures = []
    try:
        progress('inventory')
        report['device'] = client.get('info')
        turbo = client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
        machine = client.get('configs/C64%20and%20Cartridge%20Settings')
        drives = client.get('drives')
        controls = client.get('configs/U64%20Specific%20Settings/Turbo%20Control')['U64 Specific Settings']['Turbo Control']['values']
        speeds = client.get('configs/U64%20Specific%20Settings/CPU%20Speed')['U64 Specific Settings']['CPU Speed']['values']
        if 'Manual' not in controls:
            raise ValueError('Firmware does not advertise Manual turbo control')
        options = {speed: speed_option(speeds, speed) for speed in (1, 16, 64)}
        report['firmware_options'] = {'turbo': controls, 'speed': speeds}
        save('turbo-before.json', turbo)
        save('machine-before.json', machine)
        save('drives-before.json', drives)
        progress('RAM recovery capture')
        client.put('machine:pause')
        save('ram-before.bin', client.read(0, 65536))
        for speed in (1, 16, 64):
            progress(f'CIA/VIC probe Manual {speed} MHz setting')
            client.configs({'U64 Specific Settings': {'Turbo Control': 'Manual', 'CPU Speed': options[speed]}})
            active = client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
            if active['Turbo Control'] != 'Manual' or str(active['CPU Speed']).strip() != str(speed):
                raise ValueError('Requested manual setting was not applied')
            program_attempted = True  # an HTTP failure may follow partial launch
            try:
                client.run(prg, mailbox)
                ram = client.read(0, 65536)
                save(f'ram-{speed}.bin', ram)
                result = verify_capture(ram, prg, mailbox)
                save(f'verified-{speed}.json', result)
            except Exception:
                failure_capture(speed)
                raise
            captures.append((speed, ram))
            report['speeds'].append({'mhz_setting': speed,
                                     'firmware_speed_value': options[speed],
                                     'turbo_control': 'Manual', **result})
        report['calibration'] = verify_matrix(captures, prg, mailbox)
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = repr(exc)
    finally:
        progress('restore configuration and reset/resume')
        cleanup_errors = []
        if turbo is not None:
            try:
                client.configs({'U64 Specific Settings': {'Turbo Control': turbo['Turbo Control'], 'CPU Speed': turbo['CPU Speed']}})
            except Exception as exc:
                cleanup_errors.append('restore configuration: ' + repr(exc))
        reset_ok = not program_attempted
        if program_attempted:
            try:
                client.put('machine:reset')
                reset_ok = True
            except Exception as exc:
                cleanup_errors.append('reset: ' + repr(exc))
        try:
            client.put('machine:resume')
            report['reset_resumed'] = program_attempted and reset_ok
        except Exception as exc:
            cleanup_errors.append('resume: ' + repr(exc))
        if turbo is not None and machine is not None and drives is not None:
            try:
                after = client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
                machine_after = client.get('configs/C64%20and%20Cartridge%20Settings')
                drives_after = client.get('drives')
                save('turbo-after.json', after)
                save('machine-after.json', machine_after)
                save('drives-after.json', drives_after)
                if after != turbo or machine_after != machine or drive_media(drives_after) != drive_media(drives):
                    raise ValueError('Prior turbo/machine/media differs after reset/resume')
                report['configuration_restored'] = True
            except Exception as exc:
                cleanup_errors.append('verify configuration: ' + repr(exc))
        if cleanup_errors:
            report['status'] = 'failed'
            report['cleanup_errors'] = cleanup_errors
        if report['status'] == 'passed' and not (report['configuration_restored'] and report['reset_resumed']):
            report['status'] = 'failed'
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        progress('finished')
        save('result.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = run_matrix(Client(args.host), Path(__file__).resolve().parents[1], args.output.resolve())
    print(json.dumps({key: result[key] for key in ('status', 'speeds', 'configuration_restored', 'reset_resumed')}))
    raise SystemExit(result['status'] != 'passed')
