"""Final four-endpoint regression plus read-only retained SD-image type proof."""
import json
import os
import re
import time
from pathlib import Path
from readyfs_sd2iec_baseline import Baseline

TYPES = {'s': ('seq', '10'), 'p': ('prg', '11'), 'u': ('usr', '12')}

def retained_types(snapshot):
    """Require every independently exported native matrix target, not a subset."""
    found = {}
    stamps = set()
    for key, entry in snapshot.items():
        if not key.startswith('image-oracle-'):
            continue
        leaf = key.removeprefix('image-oracle-')
        match = re.fullmatch(r'(bc|bd)-([his])d([spu])([0-9]{6})\.(seq|prg|usr)', leaf)
        bridge = re.fullmatch(r'bf([0-9]{6})', leaf)
        assert entry['kind'] == 'file', key
        if match:
            operation, source, kind, stamp, extension = match.groups()
            assert extension == TYPES[kind][0]
            assert source == 'h' or kind == 's'
            found[leaf] = TYPES[kind][1]
            stamps.add(stamp)
        else:
            assert bridge, leaf
            stamps.add(bridge[1]); found[leaf] = '10'
    assert len(stamps) == 1, 'Expected one complete image matrix timestamp'
    stamp = stamps.pop()
    expected = {f'{op}-{source}d{kind}{stamp}.{TYPES[kind][0]}': TYPES[kind][1]
                for op in ('bc', 'bd') for source, kind in
                [('h', 's'), ('h', 'p'), ('h', 'u'), ('i', 's'), ('s', 's')]}
    expected['bf'+stamp] = '10'
    assert found == expected, 'Incomplete native image byte-oracle set'
    # This USR seed is also retained; it supplied the native→Ultimate USR pairs.
    expected['xu'+stamp] = '12'
    return expected

class FinalBaseline(Baseline):
    def run(self):
        self.idle = True; self.maybe_mounted = False; self.fat_verified = True
        c = self.c
        assert self.sd and self.sd_prefix.startswith('10.1:/')
        prior = Path(os.environ['READYFS_SD2IEC_IMAGE_RUN']).resolve()
        assert prior.parent == (c['ROOT']/'logs/readyfs_c64u').resolve()
        events = [json.loads(line) for line in (prior/'events.jsonl').read_text().splitlines()]
        assert events[-1].get('complete') and events[-1].get('restored') and events[-1]['result'] == 'PASS'
        passed = {event.get('case') for event in events if event.get('result') == 'PASS'}
        assert {'sd-image-matrix-independent-host-bytes',
                'ultimate-contained-image-seq-prg-usr-independent-bytes-types-removal',
                'sd-fat-to-own-image-and-back-via-explicit-intermediate'} <= passed
        scope = json.loads((prior/'continued-native-image.json').read_text())['scope']
        assert scope['owner'] == self.sd['marker']
        image = scope['path']
        assert image.startswith(self.sd_prefix+'out/')
        assert re.fullmatch(r'i[0-9]{10}\.d64', image.removeprefix(self.sd_prefix+'out/'))
        expected = retained_types(json.loads((prior/'native-image-matrix-snapshot.json').read_text()))
        stamp = next(name[2:] for name in expected if name.startswith('xu'))
        fat_bridge = self.sd_prefix+'out/br'+stamp+'.prg'
        c['save_json']('retained-native-image-types-expected.json',
                       {'prior_run': str(prior), 'image': image, 'types': expected,
                        'fat_bridge': {'path': fat_bridge, 'type': '11'}})
        super().run()
        sequence = 0
        def command(text, needle=None, pause=4):
            nonlocal sequence
            assert self.idle, 'Native command still pending'
            self.idle = False
            c['command']('CLEAR', pause=1)
            c['event'](command=text); c['keys'](text); time.sleep(.65); c['keys']([13])
            c['wait_ready'](min(pause, 4), timeout=180); self.idle = True
            sequence += 1
            if needle: c['check']('native-type-'+str(sequence).zfill(3), needle)
            return c['capture']('native-type-current')
        self.command = command
        self.guard('d', 'before-type-mount')
        self.maybe_mounted = True; self.fat_verified = False
        observed = {}
        try:
            command('MOUNT '+image+' --force', 'LAST MOUNTED BY READYFS')
            command('IEC 10: PARTITION 1', 'TYPE $02')
            command('COMPARE 10.1:/OWNER @LAB:/SDOWNER.SEQ', 'VERIFY: IDENTICAL')
            for leaf, kind in sorted(expected.items()):
                observed[leaf] = command('STAT 10.1:/'+leaf, 'TYPE: $'+kind)
            c['save_json']('retained-native-image-type-screens.json', observed)
            c['event'](case='retained-native-image-seq-prg-usr-types', result='PASS')
        finally:
            assert self.idle, 'Pending native operation; do not inject cleanup'
            command('COMPARE 10.1:/OWNER @LAB:/SDOWNER.SEQ', 'VERIFY: IDENTICAL')
            command('DISMOUNT 10.1:/ --force', 'OK')
            self.maybe_mounted = False
            self.guard('d', 'after-type-unmount')
            command('IEC 10: PARTITION 1', 'FAT OR DNP')
            self.fat_verified = True
        observed[fat_bridge] = command('STAT '+fat_bridge, 'TYPE: $11')
        c['save_json']('retained-native-image-type-screens.json', observed)
        c['event'](case='retained-native-fat-bridge-prg-type', result='PASS')

    def restore(self):
        assert getattr(self, 'idle', True), 'Native command still active'
        assert not getattr(self, 'maybe_mounted', False), 'Native image restoration unconfirmed'
        assert getattr(self, 'fat_verified', True), 'Native FAT owner restoration unconfirmed'
        super().restore()
