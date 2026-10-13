"""Continue a proved, owned SD image with IEC9/SoftwareIEC transfer pairs.

No large image upload is repeated. The supplied prior run must have completed
successfully, exported an independently checked D64, and restored its state.
"""
import hashlib
import io
import json
import os
import re
import time
from pathlib import Path
from readyfs_sd2iec_baseline import Baseline

class NativeImageMatrix(Baseline):
    def run(self):
        c=self.c
        assert self.sd and self.sd_prefix.startswith('10.1:/'), 'Image matrix requires verified partition1'
        prior=Path(os.environ['READYFS_SD2IEC_IMAGE_RUN']).resolve()
        assert prior.parent==(c['ROOT']/'logs/readyfs_c64u').resolve()
        events=[json.loads(line) for line in (prior/'events.jsonl').read_text().splitlines()]
        assert events[-1].get('complete') and events[-1].get('restored') and events[-1]['result']=='PASS'
        assert any(e.get('case')=='native-image-independent-geometry-bytes-types-source-removal' and e['result']=='PASS' for e in events)
        scope=json.loads((prior/'native-image-scope.json').read_text())
        assert scope['owner']==self.sd['marker']
        self.image_path=scope['path']
        assert self.image_path.startswith(self.sd_prefix+'out/') and self.image_path.count('/')==3
        assert re.fullmatch(r'i[0-9]{10}\.d64',self.image_path.removeprefix(self.sd_prefix+'out/'))
        assert scope['source_bytes']==174848
        c['save_json']('continued-native-image.json',{'prior_run':str(prior),'scope':scope})
        self.maybe_mounted=False
        self.fat_verified=False
        self.idle=True
        sequence=0
        def command(text,needle=None,pause=4):
            nonlocal sequence
            assert self.idle, 'Previous command did not return; do not inject more keys'
            c['command']('CLEAR',pause=1)
            c['event'](command=text);c['keys'](text);time.sleep(.65);c['keys']([13])
            self.idle=False;c['wait_ready'](min(pause,4),timeout=180);self.idle=True
            sequence+=1
            if needle:c['check']('image-matrix-'+str(sequence).zfill(3),needle)
            return c['capture']('image-matrix-current')
        self.command=command
        c['speed'](1)
        self.owned.guard(self.owned.root+'/sdowner.seq')
        with self.owned.ftp() as ftp:
            ftp.storbinary('STOR '+self.owned.root+'/sdowner.seq',io.BytesIO(self.sd['marker'].upper().encode('ascii')))
        self.guard('d','before-mount')
        c['guard_disk']()
        self.maybe_mounted=True
        try:
            command('MOUNT '+self.image_path+' --force','LAST MOUNTED BY READYFS')
            command('IEC 10: PARTITION 1','TYPE $02')
            self.image_guard()
            prefixes={'d':'10.1:/','i':'9:/','s':'s0:'+self.owned.root.removeprefix('/USB1')+'/'}
            sources={'d':'10.1:/FROMHOST','i':'9:/RFVIEW','s':prefixes['s']+'SOURCE/README'}
            expected={'d':self.owned.seed['readme.seq'],'i':(c['ROOT']/'build_support/readyfs_content_view.seq').read_bytes(),'s':self.owned.seed['readme.seq']}
            targets={}
            suffix=time.strftime('%H%M%S',time.gmtime())
            pairs=[('d','i'),('i','d'),('d','s'),('s','d')]
            self.touched_soft=True
            def path(endpoint,leaf):return prefixes[endpoint]+(leaf.removesuffix('.seq') if endpoint=='s' else leaf)
            def guard(endpoint,leaf):
                if endpoint=='d':self.image_guard()
                elif endpoint=='i':c['guard_disk']()
                else:self.owned.guard(self.owned.root+'/'+leaf.lower())
            for src,dst in pairs:
                leaf='bc-'+src+dst+suffix+'.seq';target=path(dst,leaf)
                command('STAT '+target,'NOT FOUND')
                guard(dst,leaf)
                command('COPY '+sources[src]+' '+target,'COPIED')
                command('COMPARE '+sources[src]+' '+target,'VERIFY: IDENTICAL')
                targets[leaf]=(dst,expected[src])
                c['event'](case='sd-image-copy-'+src+'-to-'+dst,result='PASS')
            for src,dst in pairs:
                src_leaf='bm-'+src+dst+suffix+'.seq';dst_leaf='bd-'+src+dst+suffix+'.seq'
                source=path(src,src_leaf);target=path(dst,dst_leaf)
                command('STAT '+source,'NOT FOUND');command('STAT '+target,'NOT FOUND')
                guard(src,src_leaf);command('COPY '+sources[src]+' '+source,'COPIED')
                guard(src,src_leaf);guard(dst,dst_leaf)
                command('MOVE '+source+' '+target,'MOVE COMPLETE')
                command('COMPARE '+sources[src]+' '+target,'VERIFY: IDENTICAL')
                command('STAT '+source,'NOT FOUND')
                targets[dst_leaf]=(dst,expected[src])
                c['event'](case='sd-image-move-'+src+'-to-'+dst,result='PASS')
            # Reopen the saved image before exporting its new logical files.
            self.image_guard();command('DISMOUNT 10.1:/ --force','OK')
            self.maybe_mounted=False;self.guard('d','after-unmount')
            self.maybe_mounted=True;command('MOUNT '+self.image_path+' --force','LAST MOUNTED BY READYFS')
            self.image_guard()
            for src,dst in pairs:
                if src=='d':command('STAT '+path(src,'bm-'+src+dst+suffix+'.seq'),'NOT FOUND')
            oracles={}
            for leaf,(endpoint,data) in targets.items():
                if endpoint!='d':continue
                oracle='image-oracle-'+leaf;self.owned.guard(self.owned.root+'/'+oracle)
                command('COPY '+path('d',leaf)+' @LAB:/'+oracle,'COPIED')
                oracles[oracle]=data
            snap=self.owned.snapshot();c['save_json']('native-image-matrix-snapshot.json',snap)
            for leaf,(endpoint,data) in targets.items():
                if endpoint=='s':assert snap[leaf]['sha256']==hashlib.sha256(data).hexdigest(),leaf
            for leaf,data in oracles.items():assert snap[leaf]['sha256']==hashlib.sha256(data).hexdigest(),leaf
            assert not any(name.startswith('bm-') for name in snap)
            c['save_json']('baseline-expected-iec-files.json',{leaf:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for leaf,(endpoint,data) in targets.items() if endpoint=='i'})
            c['event'](case='sd-image-matrix-independent-host-bytes',result='PASS')
        finally:
            if self.maybe_mounted:
                assert self.idle, 'Native command still active; cleanup not confirmed'
                # Only a successful exact image-marker comparison authorizes BACK.
                self.image_guard();command('DISMOUNT 10.1:/ --force','OK')
                self.maybe_mounted=False;self.guard('d','final-fat')
                command('IEC 10: PARTITION 1','FAT OR DNP')
                self.fat_verified=True

    def image_guard(self):
        self.owned.guard(self.owned.root+'/sdowner.seq')
        self.command('COMPARE 10.1:/OWNER @LAB:/SDOWNER.SEQ','VERIFY: IDENTICAL')

    def restore(self):
        assert getattr(self,'idle',True),'Native command still active; do not run restoration PRGs'
        assert not getattr(self,'maybe_mounted',False),'Native SD image restoration unconfirmed'
        assert getattr(self,'fat_verified',False),'Native FAT owner restoration unconfirmed'
        super().restore()
