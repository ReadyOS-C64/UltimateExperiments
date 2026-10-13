"""Native ReadyFS CLI acceptance, invoked by the Terminal-owned v3 harness.

No SD2IEC files or EEPROM are written. Temporary running settings are restored
from the exact initial X reply. Each assertion sees a freshly cleared console.
"""
import re


def run(c):
    def command(text, needle=None):
        c['command']('CLEAR', pause=1)
        c['command'](text, needle, pause=4)
        screen = c['capture']('iec-config-' + str(len(screens)).zfill(2))
        screens.append({'command': text, 'screen': screen})
        return screen

    def configuration():
        screen = command('IEC 10: CONFIG', '03,E')
        match = re.search(r'03,E([0-4][0-9A-F])([+-]):\*([+-]):I([0-9A-F]{2}):R[^\n]*', screen)
        assert match, 'Unrecognized config reply; refuse setting changes'
        return match.group(0).strip(), match.groups()

    screens = []
    c['speed'](1)
    command('HELP IEC', 'IEC 10: CONFIG')
    command('IEC 10: VERSION', '73,SD2IEC')
    original, settings = configuration()
    extension, hidden, wildcard, images = settings
    extension = int(extension, 16)
    images = int(images, 16)
    assert extension in range(5) and images in range(3)
    c['save_json']('iec-config-original.json', {'raw': original, 'extension': extension,
                                             'hidden': hidden, 'wildcard': wildcard,
                                             'images': images})
    command('IEC 10: STATUS', '00,')
    command('IEC 10: PARTITIONS', 'BOOT')
    command('IEC 10: PARTITION', 'FAT OR DNP')
    command('IEC 10: PARTITION 0', 'TYPE $FF')
    command('IEC 10: PARTITION 1', 'PARTITION $01')
    p13 = command('IEC 10: PARTITION 13')
    assert 'PARTITION ABSENT' in p13 or 'PARTITION $0D' in p13, 'Partition 13 became a current-partition query'
    command('IEC 10: DOS "X?"', '09,')
    command('IEC 10: EXTENSIONS', 'USAGE:')
    unchanged, _ = configuration()
    assert unchanged == original, 'Read-only and invalid-usage commands changed config'
    touched = False
    try:
        # Only modes 1/2: they leave extension hiding unchanged.
        touched = True
        command('IEC 10: EXTENSIONS ' + str(2 if extension != 2 else 1), '03,E')
        command('IEC 10: IMAGES ' + ('both' if images != 2 else 'files'), '00,')
    finally:
        if touched:
            command('IEC 10: EXTENSIONS ' + str(extension), '03,E')
            command('IEC 10: HIDE-EXTENSIONS ' + ('on' if hidden == '+' else 'off'), '03,E')
            command('IEC 10: IMAGES ' + ('files', 'dirs', 'both')[images], '00,')
            restored, _ = configuration()
            assert restored == original, (original, restored)
            c['event'](case='iec-config-running-settings-restored', result='PASS')
        c['save_json']('iec-config-screens.json', screens)
    for mhz in (16, 64):
        c['speed'](mhz)
        command('IEC 10: VERSION', '73,SD2IEC')
        command('IEC 10: PARTITION 1', 'PARTITION $01')
        c['event'](case=f'iec-config-native-read-{mhz}mhz', result='PASS')
    c['speed'](1)
    c['save_json']('iec-config-screens.json', screens)
    c['event'](case='iec-config-physical-cli', result='PASS')
