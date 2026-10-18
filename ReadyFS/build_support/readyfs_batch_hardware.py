"""Physical Ultimate acceptance, called by the Terminal-owned v3 harness.

All storage writes stay in its newly created marker-owned USB1 root. Drive A
is preserved; the harness restores drive B and CPU settings. Readiness uses
passive VIC frames, never memory polling during filesystem operations.
"""
import hashlib
import io


def run(c):
    owned = c['owned']
    screens = []
    outcomes = []

    def command(text, needle=None):
        c['command']('CLEAR', pause=1)
        c['command'](text, needle, pause=3)
        screen = c['capture']('batch-' + str(len(screens)).zfill(2))
        screens.append({'command': text, 'screen': screen})
        c['save_json']('batch-screens.json', screens)
        return screen

    def upload(leaf, data):
        path = owned.root + '/' + leaf
        owned.guard(path)
        with owned.ftp() as ftp:
            # Every name is fresh below this run's unique root.
            ftp.storbinary('STOR ' + path, io.BytesIO(data))

    def download(leaf):
        path = owned.root + '/' + leaf
        owned.guard(path)
        result = io.BytesIO()
        with owned.ftp() as ftp:
            ftp.retrbinary('RETR ' + path, result.write)
        return result.getvalue()

    script = '''REM PHYSICAL ULTIMATE DOS BATCH
SET ROOT=%1
SET SRC=%ROOT%SOURCE/README.SEQ
SET OUT=%ROOT%%2
SET /A N=0
:LOOP
SET /A N=N+1
IF %N% LSS 3 GOTO LOOP
IF NOT DEFINED SRC EXIT /B 9
IF NOT EXIST "%SRC%" EXIT /B 9
COPY "%SRC%" "%OUT%"
EXPECT RC 0
IF NOT EXIST "%OUT%" EXIT /B 9
COMPARE "%SRC%" "%OUT%"
EXPECT RC 0
CALL :FINISH
ONERROR CONTINUE
NOTACOMMAND
IF NOT ERRORLEVEL 1 EXIT /B 9
ECHO HARDWARE RC PASS %ERRORLEVEL%
ECHO HARDWARE FLOW PASS %3 %N%
EXIT /B 0
:FINISH
ECHO SUBROUTINE PASS
EXIT /B 0
'''.replace('\n', '\r').encode('ascii')
    upload('batch.seq', script)
    upload('bad.seq', b'SET DEST=%1\rWRITE %DEST% "%BROKEN\rECHO SHOULD NEVER RUN\r')
    legacy = bytes([0xD2, 0xC6, 0xC3, 0x31, 8, 16, 255, 0]) + b'9:/' + bytes(253 + 8 * 273)
    upload('legacy.seq', legacy)
    upload('badcfg.seq', legacy[:3] + b'2' + legacy[4:] + bytes(10))
    fixture = owned.seed['readme.seq']
    command('HELP BATCH', 'SET /P')
    for mhz in (1, 16, 64):
        c['speed'](mhz)
        output = f'result-{mhz}.seq'
        owned.guard(owned.root + '/' + output)
        screen = command(f'RUN @LAB:/BATCH.SEQ @LAB:/ {output.upper()} {mhz}',
                         f'HARDWARE FLOW PASS {mhz} 3')
        assert 'HARDWARE RC PASS 1' in screen and 'RC 0' in screen, screen
        data = download(output)
        assert data == fixture, 'UltimateDOS batch copy byte mismatch'
        c['event'](case=f'batch-native-copy-and-flow-{mhz}mhz', result='PASS')
        config = f'cfg-{mhz}.seq'
        command(f'SET /P SAVED=VALUE-{mhz}')
        command(f'SET PRIVATE=SESSION-{mhz}')
        owned.guard(owned.root + '/' + config)
        command(f'CONFIG SAVE @LAB:/{config.upper()}', 'CONFIG SAVED AND VERIFIED')
        saved = download(config)
        # cc65's uppercase C literals use shifted PETSCII, as in RFC1.
        assert saved[:8] == bytes([0xD2, 0xC6, 0xC3, 0x32, 8, 16, 255, 0]) and len(saved) == 4784, (saved[:8], len(saved))
        records = []
        for offset in range(2448, len(saved), 146):
            record = saved[offset:offset + 146]
            name = record[:17].split(b'\0')[0]
            if name:
                records.append((name, record[17:145].split(b'\0')[0], record[145]))
        assert records == [(b'SAVED', f'VALUE-{mhz}'.encode(), 1)], records
        (c['OUT'] / f'config-{mhz}.bin').write_bytes(saved)
        command('SET /P SAVED=CHANGED')
        command('SET /P LATER=REMOVE')
        command('SET PRIVATE=STILLHERE')
        command(f'CONFIG LOAD @LAB:/{config.upper()}', 'CONFIG LOADED')
        command('ECHO VALUES %SAVED% %PRIVATE% [%LATER%]', f'VALUES VALUE-{mhz} STILLHERE []')
        c['event'](case=f'batch-config-byte-oracle-{mhz}mhz', result='PASS')
        outcomes.append({'mhz': mhz, 'copy_sha256': hashlib.sha256(data).hexdigest(),
                         'config_sha256': hashlib.sha256(saved).hexdigest()})
        c['save_json']('batch-outcomes.json', outcomes)
    command('CONFIG LOAD @LAB:/BADCFG.SEQ', 'BAD CFG; UNCHANGED')
    command('ECHO REJECT %SAVED% %PRIVATE%', 'REJECT VALUE-64 STILLHERE')
    command('ALIAS', '@LAB:')
    c['event'](case='batch-truncated-config-keeps-session', result='PASS')
    before = download('source/readme.seq')
    command('RUN @LAB:/BAD.SEQ @LAB:/SOURCE/README.SEQ', 'BAD EXPANSION/QUOTES/ARGS')
    assert download('source/readme.seq') == before, 'Malformed expansion reached a write'
    c['event'](case='batch-expansion-before-mutation', result='PASS')

    # Relaunch the exact admitted build: config persists on USB1, while the
    # session environment must start empty. The outer harness still owns B.
    c['speed'](64)
    c['hardware_wait_unresolved'] = True
    response = c['api']('/runners:run_prg', 'POST', bytes(c['binary']), 'application/octet-stream', 45)
    (c['OUT'] / 'batch-relaunch.json').write_bytes(response)
    c['wait_ready'](5, timeout=300)
    command('ECHO INITIAL [%SAVED%] [%PRIVATE%]', 'INITIAL [] []')
    command('CONFIG LOAD u:' + owned.root + '/CFG-64.SEQ', 'CONFIG LOADED')
    command('ECHO FRESH %SAVED% [%PRIVATE%]', 'FRESH VALUE-64 []')
    c['event'](case='batch-physical-restart-persistence', result='PASS')
    command('CONFIG LOAD u:' + owned.root + '/LEGACY.SEQ', 'CONFIG LOADED')
    command('PWD', '9:/')
    command('ECHO LEGACY %SAVED%', 'LEGACY VALUE-64')
    c['event'](case='batch-legacy-rfc1-keeps-variables', result='PASS')
    assert download('source/readme.seq') == fixture
    c['save_json']('batch-screens.json', screens)
    c['event'](case='batch-physical-ultimate-acceptance', result='PASS')
