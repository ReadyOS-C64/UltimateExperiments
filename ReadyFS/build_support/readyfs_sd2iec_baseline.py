"""Existing endpoint matrix, run in the Terminal-owned v3 hardware harness.

This does not write to SD2IEC. All mutations use its harness's fresh owned
Ultimate subtree or disposable B9 disk. SoftwareIEC accesses that same owned
host subtree through its existing mapping; native cwd is restored afterward.
"""
import hashlib
import json
import subprocess
import time

class Baseline:
    def __init__(self, context):
        self.c = context
        self.touched_soft = False
        self.owned = context['owned']
        self.out = context['OUT']
        drives = context['js']('/drives')
        software = next(d['IEC Drive'] for d in drives['drives'] if 'IEC Drive' in d)
        assert software['bus_id'] == 11 and software['enabled']
        self.before_path = next(p['path'] for p in software['partitions'] if p['id'] == 0)
        self.before_config = context['js']('/configs/SoftIEC%20Drive%20Settings')
        configured = self.before_config['SoftIEC Drive Settings']['Default Path']
        assert self.before_path.rstrip('/').lower() == configured.rstrip('/').lower(), 'Unknown SoftwareIEC cwd: preserve it rather than guessing restoration'
        self.prg = self.out/'softiec-reset-root.prg'
        subprocess.run(['cl65','-t','c64','-Os','-o',str(self.prg),str(context['ROOT']/'build_support/readyfs_softiec_reset_root.c')],check=True)
        context['save_json']('baseline-softiec-before.json', {'drives':software,'configuration':self.before_config})

    def guard(self, endpoint, leaf):
        if endpoint == 'i': self.c['guard_disk']()
        else: self.owned.guard(self.owned.root+'/'+leaf.lower())

    def run(self):
        c = self.c
        def command(text, needle=None, pause=4):
            # Every assertion must refer to this operation, never old scrollback.
            c['command']('CLEAR', pause=1)
            c['command'](text, needle, pause)
        self.owned.guard(self.owned.root+'/media.d81')
        state=c['js']('/drives')
        assert not next(d['b'] for d in state['drives'] if 'b' in d).get('image_file'),'Expected the baseline dismount to leave B empty'
        command('MOUNT @LAB:/MEDIA.D81 9: --force','LAST MOUNTED BY READYFS',4)
        c['guard_disk']()
        command('PROBE IEC 10:',pause=4)
        observed = c['capture']('sd2iec-readonly-identity')
        c['event'](sd2iec_identity=observed, result='OBSERVATION')
        root = self.owned.root
        # Existing SoftwareIEC backend bridges s0:/ to USB1, then walks components.
        soft_root = root.removeprefix('/USB1')
        prefixes = {'u':'@LAB:/','i':'9:/','s':'s0:'+soft_root+'/'}
        sources = {'u':'@LAB:/SOURCE/README.SEQ','i':'9:/RFVIEW','s':'s0:'+soft_root+'/SOURCE/README'}
        expected = {'u':b'READYFS NESTED DEMO\rSOURCE STAYS SAFE\r',
                    's':b'READYFS NESTED DEMO\rSOURCE STAYS SAFE\r',
                    'i':(c['ROOT']/'build_support/readyfs_content_view.seq').read_bytes()}
        self.touched_soft = True
        def pathname(endpoint, leaf):
            # SoftwareIEC exposes the CBM logical stem; SEQ is its file type.
            # Sending a .seq suffix as part of the logical stem creates .seq.seq.
            return prefixes[endpoint] + (leaf.removesuffix('.seq') if endpoint == 's' else leaf)
        targets = {}
        for source in prefixes:
            for destination in prefixes:
                if source == destination: continue
                leaf = 'bc-'+source+destination+'.seq'
                target = pathname(destination,leaf)
                self.guard(destination,leaf)
                command('COPY '+sources[source]+' '+target,'COPIED',5)
                command('COMPARE '+sources[source]+' '+target,'VERIFY: IDENTICAL',5)
                targets[leaf] = (destination,expected[source])
                c['event'](case='baseline-copy-'+source+'-to-'+destination,result='PASS')
        for source in prefixes:
            for destination in prefixes:
                if source == destination: continue
                src_leaf='bm-'+source+destination+'.seq'; dst_leaf='bd-'+source+destination+'.seq'
                source_path=pathname(source,src_leaf); destination_path=pathname(destination,dst_leaf)
                self.guard(source,src_leaf)
                command('COPY '+sources[source]+' '+source_path,'COPIED',5)
                self.guard(source,src_leaf);self.guard(destination,dst_leaf)
                command('MOVE '+source_path+' '+destination_path,'MOVE COMPLETE',5)
                command('COMPARE '+sources[source]+' '+destination_path,'VERIFY: IDENTICAL',5)
                targets[dst_leaf]=(destination,expected[source])
                c['event'](case='baseline-move-'+source+'-to-'+destination,result='PASS')
        snap = self.owned.snapshot(); c['save_json']('baseline-endpoint-snapshot.json',snap)
        for leaf,(endpoint,data) in targets.items():
            if endpoint == 'i':continue # persisted D81 is checked after unmount/flush
            assert snap[leaf]['sha256'] == hashlib.sha256(data).hexdigest(),leaf
        assert not any(name.startswith('bm-') for name in snap),'Host move source remains'
        c['save_json']('baseline-expected-iec-files.json',{
            leaf:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            for leaf,(endpoint,data) in targets.items() if endpoint=='i'})
        c['event'](case='baseline-host-independent-byte-oracle',result='PASS')

    def restore(self):
        if not self.touched_soft:return
        c=self.c;c['speed'](1)
        c['write'](0xC1F0,b'\0')
        c['api']('/runners:run_prg','POST',self.prg.read_bytes(),'application/octet-stream')
        deadline=time.monotonic()+30
        while c['read'](0xC1F0,1)!=b'\xA5':
            assert time.monotonic()<deadline,'SoftwareIEC cwd restoration did not finish'
            time.sleep(.5)
        drives=c['js']('/drives')
        software=next(d['IEC Drive'] for d in drives['drives'] if 'IEC Drive' in d)
        after=next(p['path'] for p in software['partitions'] if p['id']==0)
        assert after.rstrip('/').lower()==self.before_path.rstrip('/').lower(),(after,self.before_path)
        assert c['js']('/configs/SoftIEC%20Drive%20Settings')==self.before_config
        c['save_json']('baseline-softiec-restored.json',software)
        c['event'](case='baseline-softiec-cwd-and-config-restored',result='PASS')
