"""Exercise emitted save policy with real provider code/model-ROM filesystem.

The coordinator here is deliberately host-side; integrating the same bounded
actions into the resident editor and native D81 failure tests remains M4 work.
"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fileio_fixture import FileIOFixture

OK, FAILED, MATCH, MISMATCH, UNCERTAIN = 1,2,3,4,5
CREATE, WRITE, CLOSE, OPEN_VERIFY, COMPARE, CLOSE_VERIFY = 1,2,3,4,5,6
BACKUP, PROMOTE, CHECK, DELETE_BACKUP, DONE, ABORT, DELETE_TEMP, ROLLBACK, RECOVERY = range(7,16)

f=FileIOFixture()
cases=[]
try:
    # Invalid entry points do not silently reset an active save/recovery job.
    f.call('se_sv_begin',a=2,error=0x97)
    f.call('se_sv_step',error=0x97)
    f.call('se_sv_begin')
    f.call('se_sv_begin',error=0x97)
    f.call('se_sv_step',a=MATCH,error=0x97)
    f.set('se_sv_phase',DONE)
    for had_target in (0,1):
        f.call('se_sv_begin',a=had_target)
        expected = [CREATE,WRITE,CLOSE,OPEN_VERIFY,COMPARE,CLOSE_VERIFY]
        expected += ([BACKUP] if had_target else []) + [PROMOTE,CHECK]
        expected += ([DELETE_BACKUP] if had_target else []) + [DONE]
        observed=[]
        while f.read('se_sv_phase')[0] != DONE:
            phase=f.read('se_sv_phase')[0];observed.append(phase)
            f.call('se_sv_step',a=MATCH if phase==COMPARE else OK)
        observed.append(DONE)
        assert observed==expected,(observed,expected)
    cases.append('new/overwrite action order and required byte comparison')

    # Every uncertain acknowledgement freezes without requesting destruction.
    for phase in range(CREATE,RECOVERY):
        if phase==DONE:continue
        f.set('se_sv_phase',phase)
        f.call('se_sv_step',a=UNCERTAIN)
        assert f.read('se_sv_phase')[0]==RECOVERY
        f.call('se_sv_step',a=OK,error=0x97)
    cases.append('all uncertain actions retain files and require explicit recovery')

    def run(existing=True, fail=None, uncertain=False, mismatch=False, cancel=None):
        target, temp, backup=b'doc',b'SE000001T',b'SE000001B'
        old=b'old document\r';new=bytes(range(256))*5+b'\rNEW\0\x93'
        f.call('se_io_init');f.fs={target:old} if existing else {}
        f.set('se_sv_phase',DONE);f.call('se_sv_begin',a=int(existing))
        seen=[]
        while f.read('se_sv_phase')[0] not in (DONE,RECOVERY):
            state=f.read('se_sv_phase')[0];seen.append(state)
            assert len(seen)<30
            if state==cancel:
                f.set('se_sv_error',0x80);f.call('se_sv_step',a=0);continue
            if state==fail:
                if state in (CLOSE,CLOSE_VERIFY):f.call('se_io_abort')
                f.set('se_sv_error',0x92)
                f.call('se_sv_step',a=UNCERTAIN if uncertain else FAILED)
                continue
            event=OK
            if state==CREATE:
                f.name(temp);f.call('se_io_create_temp')
            elif state==WRITE:
                for pos in range(0,len(new),256):
                    part=new[pos:pos+256];f.m.load(0x8000,part)
                    f.set('se_io_count',len(part)&255);f.call('se_io_write_chunk')
            elif state in (CLOSE,CLOSE_VERIFY):
                f.call('se_io_close')
            elif state==OPEN_VERIFY:
                f.name(temp);f.call('se_io_open_read')
            elif state==COMPARE:
                actual=bytearray()
                while not f.read('se_io_eof')[0]:
                    f.set('se_io_count',0);f.call('se_io_read_chunk')
                    n=int.from_bytes(f.read('se_io_done',2),'little')
                    actual.extend(f.read(0x8000,n))
                event=MATCH if bytes(actual)==new and not mismatch else MISMATCH
                if event==MISMATCH:f.set('se_sv_error',0x98)
            elif state==BACKUP:
                f.name(target);f.name(backup,True);f.call('se_io_make_backup')
            elif state==PROMOTE:
                f.name(temp);f.name(target,True);f.call('se_io_rename')
            elif state==CHECK:
                # Reopen and compare promoted bytes, then close before reporting.
                f.name(target);f.call('se_io_open_read');actual=bytearray()
                while not f.read('se_io_eof')[0]:
                    f.set('se_io_count',0);f.call('se_io_read_chunk')
                    n=int.from_bytes(f.read('se_io_done',2),'little')
                    actual.extend(f.read(0x8000,n))
                f.call('se_io_close');assert bytes(actual)==new
            elif state==DELETE_BACKUP:f.call('se_io_scratch_owned',a=1)
            elif state==ABORT:f.call('se_io_abort')
            elif state==DELETE_TEMP:f.call('se_io_scratch_owned')
            elif state==ROLLBACK:
                f.name(backup);f.name(target,True);f.call('se_io_rename')
            else:raise AssertionError(state)
            f.call('se_sv_step',a=event)
        phase=f.read('se_sv_phase')[0]
        # RECOVERY may keep a data channel open; coordinator closes it without
        # discarding capabilities or mutating the disk names.
        f.call('se_io_abort');assert not f.channels
        if fail is None and not mismatch and cancel is None:
            assert phase==DONE and f.fs=={target:bytearray(new)}
        elif phase==DONE:
            assert f.fs==({target:old} if existing else {})
        else:
            assert phase==RECOVERY
            assert any(bytes(data)==old for data in f.fs.values()) if existing else True
        return dict(existing=existing,fail=fail,uncertain=uncertain,mismatch=mismatch,
                    cancel=cancel,states=seen,final=phase,
                    files={k.decode('ascii'):hashlib.sha256(v).hexdigest() for k,v in f.fs.items()})
    results=[]
    for existing in [False,True]:
        results.append(run(existing))
        results.append(run(existing,mismatch=True))
        for phase in [CREATE,WRITE,CLOSE,OPEN_VERIFY,CLOSE_VERIFY,PROMOTE]:
            results.append(run(existing,fail=phase))
        for phase in [CREATE,WRITE,CLOSE,OPEN_VERIFY,COMPARE,CLOSE_VERIFY,PROMOTE,CHECK]:
            results.append(run(existing,fail=phase,uncertain=True))
        for phase in [CREATE,WRITE,OPEN_VERIFY,CLOSE_VERIFY]:
            results.append(run(existing,cancel=phase))
    results.append(run(True,fail=BACKUP))
    results.append(run(True,fail=BACKUP,uncertain=True))
    results.append(run(True,fail=DELETE_BACKUP))
    cases.append('provider-coordinated success, mismatch, cancel, rollback and interruption scenarios')
    result=dict(pass_=True,cases=cases,scenarios=results,scope='emitted save policy/provider with modeled ROM; coordinator is host test only')
    (ROOT/'build/fileio/save-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_=True,cases=cases,scenarios=len(results)),indent=2))
finally:f.close()
