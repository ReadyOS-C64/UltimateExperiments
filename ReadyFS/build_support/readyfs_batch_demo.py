"""Record one parameterized backup script on the physical C64 Ultimate.

Uses the existing Terminal-owned recorder, fresh owned root and passive VIC
completion checks. No existing files, SD2IEC settings or drive A are changed.
"""
import hashlib
import io
import time


class BatchDemo:
    def __init__(self, context):
        self.c = context
        self.idle = True

    def hidden(self, text):
        c = self.c
        assert self.idle
        self.idle = False
        c['hardware_wait_unresolved'] = True
        c['event'](hidden_command=text)
        c['keys'](text, False)
        c['keys']([13], False)
        c['wait_ready'](2, timeout=240)
        self.idle = True

    def command(self, text, needle=None, explanation='', pages=False):
        c = self.c
        self.hidden('CLEAR')
        start = time.time()
        c['event'](command=text)
        self.idle = False
        c['hardware_wait_unresolved'] = True
        c['keys'](text)
        time.sleep(.45)
        typed = time.time()
        c['keys']([13], False)
        c['wait_ready'](3, timeout=240)
        self.idle = True
        earlier = []
        for number in range(12):
            screen = c['capture']('current-batch-demo')
            if '-- MORE --' not in screen.upper():
                break
            assert pages, 'Unexpected paging'
            name = f'batch-page-{len(c["steps"])+1:02d}-{number+1:02d}.png'
            c['snapshot_png'](name)
            earlier.append({'screenshot': name, 'screen': screen})
            time.sleep(5)
            self.idle = False
            c['hardware_wait_unresolved'] = True
            c['keys'](' ', False)
            c['wait_ready'](3, timeout=240)
            self.idle = True
        else:
            raise AssertionError('Too many script pages')
        if needle:
            c['check']('batch-demo-' + str(len(c['steps'])+1).zfill(2), needle)
        if pages and text.startswith('TYPE ') and not earlier:
            # TYPE streams text; use normal output history to read the first
            # half after it scrolls away. Never poll memory during its I/O.
            for number in range(2):
                c['keys']([133], False)
                time.sleep(2)
                name = f'batch-page-{len(c["steps"])+1:02d}-{number+1:02d}.png'
                c['snapshot_png'](name)
                screen = c['capture']('batch-script-history-' + str(number))
                earlier.append({'screenshot': name, 'screen': screen})
                time.sleep(5)
            c['keys']([3], False)
            time.sleep(1)
        c['record_step'](text, explanation=explanation, started=start)
        step = c['steps'][-1]
        step['typed_epoch'] = typed
        if earlier:
            step['pages'] = earlier
        time.sleep(4)
        step['end_epoch'] = time.time()

    def run(self):
        c = self.c
        owned = c['owned']
        script = (c['ROOT']/'build_support/readyfs_backup.seq').read_text()
        data = script.replace('\n', '\r').encode('ascii')
        path = owned.root + '/backup.seq'
        owned.guard(path)
        with owned.ftp() as ftp:
            ftp.storbinary('STOR ' + path, io.BytesIO(data))
        (c['OUT']/'backup.seq').write_bytes(data)
        self.hidden('ALIAS LAB u:' + owned.root)
        c['speed'](1)
        c['chapter']('10 · Parameterized batch backup',
                     'Read one script, preview it, then verify a backup.')
        self.command('SET BACKUPS=0', explanation='A named session variable counts successful backups across runs.')
        self.command('TYPE @LAB:/BACKUP.SEQ', 'EXIT /B 4',
                     'Read the actual script: arguments, conditions, labels, a local CALL and a counter.', pages=True)
        before = owned.snapshot()
        invocation = 'RUN @LAB:/BACKUP.SEQ @LAB:/SOURCE/README.SEQ @LAB:/SAVED.SEQ '
        self.command(invocation + 'PREVIEW', 'RC 0',
                     'Pass source, destination and PREVIEW as %1, %2 and %3; no file is written.')
        after = owned.snapshot()
        c['save_json']('preview-before.json', before)
        c['save_json']('preview-after.json', after)
        assert after == before, 'Preview changed storage'
        c['event'](case='batch-demo-preview-unchanged', result='PASS')
        owned.guard(owned.root + '/saved.seq')
        self.command(invocation + 'APPLY', 'BACKUPS THIS SESSION: 1',
                     'Pass APPLY to copy and compare; CALL shares SRC/DST and arithmetic increments BACKUPS.')
        result = io.BytesIO()
        with owned.ftp() as ftp:
            ftp.retrbinary('RETR ' + owned.root + '/saved.seq', result.write)
        assert result.getvalue() == owned.seed['readme.seq'], 'Backup differs from source'
        c['event'](case='batch-demo-backup-independent-bytes', result='PASS')
        snap = owned.snapshot()
        self.command(invocation + 'APPLY', 'RC 6',
                     'An existing destination takes the refusal branch, returns 6 and leaves the counter unchanged.')
        assert owned.snapshot() == snap, 'Existing destination was modified'
        c['event'](case='batch-demo-existing-destination-unchanged', result='PASS')
        self.command('TYPE @LAB:/SAVED.SEQ', 'SOURCE STAYS SAFE',
                     'Read the copied file and see the original fixture text.')
        self.command('ECHO COMPLETED BACKUPS: %BACKUPS%', 'COMPLETED BACKUPS: 1',
                     'Script changes to named variables remain available at the interactive prompt.')
        assert owned.subtree(owned.snapshot(), 'source') == owned.subtree(owned.original, 'source')
        c['save_json']('batch-demo-checks.json', {
            'script_sha256': hashlib.sha256(data).hexdigest(),
            'backup_sha256': hashlib.sha256(result.getvalue()).hexdigest(),
            'backup_bytes': len(result.getvalue()),
            'source_preserved': True, 'preview_unchanged': True,
            'existing_destination_unchanged': True,
            'root': owned.root, 'script': 'backup.seq',
            'parameters': ['@LAB:/SOURCE/README.SEQ', '@LAB:/SAVED.SEQ', 'PREVIEW or APPLY'],
        })
        c['event'](case='batch-demo-source-preserved-and-shared-counter', result='PASS')

    def restore(self):
        assert self.idle, 'Command unresolved; leave recovery to the recorder'
