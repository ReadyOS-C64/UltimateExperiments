"""Continue a proved, owned SD image with native/SoftIEC/typed UDOS pairs.

No large image upload is repeated. The supplied prior run must have completed
successfully, exported an independently checked D64, and restored its state.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import time
from pathlib import Path
from readyfs_sd2iec_baseline import Baseline

IMAGE_TYPES={'s':'seq','p':'prg','u':'usr'}
# Exercise the newly integrated typed image service first; retain every pair.
IMAGE_PAIRS=[(src,dst,kind) for kind in IMAGE_TYPES
    for src,dst in [('d','h'),('h','d')]]+[
    ('d','i','s'),('i','d','s'),('d','s','s'),('s','d','s')]
def matrix_leaf(operation,source,destination,kind,suffix):
    leaf=operation+'-'+source+destination+kind+suffix+'.'+IMAGE_TYPES[kind]
    assert len(leaf)<=16 and '/' not in leaf
    return leaf

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
            self.idle=False
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
        # Separate unmounted host image: never access B9's container concurrently.
        payload=(prior/'image-hello.prg').read_bytes()
        assert payload==b'\x01\x08'+bytes((i*13+7)&255 for i in range(513))
        owner_file=self.out/'ud-image-owner.seq';owner_file.write_bytes(self.sd['marker'].upper().encode('ascii'))
        hello_file=self.out/'ud-image-hello.prg';hello_file.write_bytes(payload)
        note_file=self.out/'ud-image-note.seq';note_file.write_bytes(self.owned.seed['readme.seq'])
        data_file=self.out/'ud-image-data.usr';data_file.write_bytes(bytes((i*17+3)&255 for i in range(129)))
        host_image=self.out/'ud-image.d64'
        subprocess.run(['c1541','-format','readyfs ud,rf','d64',str(host_image),
            '-write',str(owner_file),'owner,s','-write',str(hello_file),'hello,p',
            '-write',str(note_file),'note,s','-write',str(data_file),'data,u'],check=True,capture_output=True)
        self.owned.guard(self.owned.root+'/ud-image.d64')
        with self.owned.ftp() as ftp:
            ftp.storbinary('STOR '+self.owned.root+'/ud-image.d64',io.BytesIO(host_image.read_bytes()))
        # Explicit same-device bridge: all channels close before changing
        # the SD filesystem view. The host file is an independently hashed
        # intermediate, never a Mac runtime relay.
        bridge_seed=bytes((i*37+11)&255 for i in range(1025))
        self.owned.guard(self.owned.root+'/fat-to-image.seq')
        command('COPY '+self.sd_prefix+'in/seed @LAB:/FAT-TO-IMAGE.SEQ','COPIED')
        command('COMPARE '+self.sd_prefix+'in/seed @LAB:/FAT-TO-IMAGE.SEQ','VERIFY: IDENTICAL')
        self.guard('d','before-mount')
        c['guard_disk']()
        self.maybe_mounted=True
        try:
            command('MOUNT '+self.image_path+' --force','LAST MOUNTED BY READYFS')
            command('IEC 10: PARTITION 1','TYPE $02')
            self.image_guard()
            prefixes={'d':'10.1:/','i':'9:/','s':'s0:'+self.owned.root.removeprefix('/USB1')+'/','h':'@LAB:/UD-IMAGE.D64/'}
            sources={'d':'10.1:/FROMHOST','i':'9:/RFVIEW','s':prefixes['s']+'SOURCE/README'}
            expected={'d':self.owned.seed['readme.seq'],'i':(c['ROOT']/'build_support/readyfs_content_view.seq').read_bytes(),'s':self.owned.seed['readme.seq']}
            targets={}
            suffix=time.strftime('%H%M%S',time.gmtime())
            bridge_image_leaf='bf'+suffix
            command('STAT 10.1:/'+bridge_image_leaf,'NOT FOUND')
            self.image_guard();command('COPY @LAB:/FAT-TO-IMAGE.SEQ 10.1:/'+bridge_image_leaf,'COPIED')
            command('COMPARE @LAB:/FAT-TO-IMAGE.SEQ 10.1:/'+bridge_image_leaf,'VERIFY: IDENTICAL')
            targets[bridge_image_leaf]=('d',bridge_seed)
            self.owned.guard(self.owned.root+'/image-to-fat.prg')
            command('COPY 10.1:/HELLO @LAB:/IMAGE-TO-FAT.PRG','COPIED')
            command('COMPARE 10.1:/HELLO @LAB:/IMAGE-TO-FAT.PRG','VERIFY: IDENTICAL')
            pairs=IMAGE_PAIRS
            image_sources={'s':prefixes['h']+'NOTE.SEQ','p':prefixes['h']+'HELLO.PRG','u':prefixes['h']+'DATA.USR'}
            image_data={'s':note_file.read_bytes(),'p':payload,'u':data_file.read_bytes()}
            usr_seed='xu'+suffix
            command('STAT 10.1:/'+usr_seed,'NOT FOUND')
            self.image_guard();command('COPY '+image_sources['u']+' 10.1:/'+usr_seed,'COPIED')
            command('COMPARE '+image_sources['u']+' 10.1:/'+usr_seed,'VERIFY: IDENTICAL')
            def pair_source(src,dst,kind):
                if src=='h':return image_sources[kind]
                if src=='d' and dst=='h':return '10.1:/'+{'s':'FROMHOST','p':'HELLO','u':usr_seed}[kind]
                return sources[src]
            def pair_expected(src,dst,kind):
                return image_data[kind] if 'h' in (src,dst) else expected[src]
            def make_leaf(operation,src,dst,kind):return matrix_leaf(operation,src,dst,kind,suffix)
            self.touched_soft=True
            def path(endpoint,leaf):
                # Bare COPY names inherit type; MOVE destinations additionally
                # exercise explicit typed selectors in the UDOS image view.
                return prefixes[endpoint]+(leaf.removesuffix('.seq') if endpoint=='s' else
                    leaf.rsplit('.',1)[0] if endpoint=='h' and not leaf.startswith('bd-') else leaf)
            def guard(endpoint,leaf):
                if endpoint=='d':self.image_guard()
                elif endpoint=='i':c['guard_disk']()
                elif endpoint=='h':self.owned.guard(self.owned.root+'/ud-image.d64')
                else:self.owned.guard(self.owned.root+'/'+leaf.lower())
            for src,dst,kind in pairs:
                name=make_leaf('bc',src,dst,kind);target=path(dst,name)
                command('STAT '+target,'NOT FOUND')
                guard(dst,name)
                command('COPY '+pair_source(src,dst,kind)+' '+target,'COPIED')
                command('COMPARE '+pair_source(src,dst,kind)+' '+target,'VERIFY: IDENTICAL')
                targets[name]=(dst,pair_expected(src,dst,kind))
                c['event'](case='sd-image-copy-'+src+'-to-'+dst+'-'+IMAGE_TYPES[kind],result='PASS')
            for src,dst,kind in pairs:
                src_leaf=make_leaf('bm',src,dst,kind);dst_leaf=make_leaf('bd',src,dst,kind)
                source=path(src,src_leaf);target=path(dst,dst_leaf)
                command('STAT '+source,'NOT FOUND');command('STAT '+target,'NOT FOUND')
                guard(src,src_leaf);command('COPY '+pair_source(src,dst,kind)+' '+source,'COPIED')
                guard(src,src_leaf);guard(dst,dst_leaf)
                command('MOVE '+source+' '+target,'MOVE COMPLETE')
                command('COMPARE '+pair_source(src,dst,kind)+' '+target,'VERIFY: IDENTICAL')
                command('STAT '+source,'NOT FOUND')
                targets[dst_leaf]=(dst,pair_expected(src,dst,kind))
                c['event'](case='sd-image-move-'+src+'-to-'+dst+'-'+IMAGE_TYPES[kind],result='PASS')
            # Force replacement changes an existing SEQ to PRG while retaining
            # its old type in the backup. Then rename and reject alias moves.
            replacement='rp'+suffix;renamed='rn'+suffix;rejected='rx'+suffix
            for leaf in (replacement,renamed,rejected):command('STAT '+prefixes['h']+leaf,'NOT FOUND')
            guard('h',replacement);command('COPY '+image_sources['s']+' '+prefixes['h']+replacement,'COPIED')
            guard('h',replacement);command('COPY '+image_sources['p']+' '+prefixes['h']+replacement+' --force','COPIED')
            command('COMPARE '+image_sources['p']+' '+prefixes['h']+replacement+'.PRG','VERIFY: IDENTICAL')
            guard('h',replacement);command('RENAME '+prefixes['h']+replacement+' '+prefixes['h']+renamed,'RENAME COMPLETE')
            command('STAT '+prefixes['h']+replacement,'NOT FOUND')
            targets[renamed+'.prg']=('h',payload)
            guard('h',renamed)
            command('MOVE '+prefixes['h']+renamed+'.PRG '+prefixes['h']+renamed+' --force','SAME IMAGE ENTRY')
            command('COMPARE '+image_sources['p']+' '+prefixes['h']+renamed+'.PRG','VERIFY: IDENTICAL')
            guard('h',renamed)
            command('RENAME '+prefixes['h']+renamed+'.PRG '+prefixes['h']+renamed+' --force','SAME IMAGE ENTRY')
            command('COMPARE '+image_sources['p']+' '+prefixes['h']+renamed+'.PRG','VERIFY: IDENTICAL')
            guard('h',rejected)
            command('COPY '+image_sources['s']+' '+prefixes['h']+rejected+'.PRG','IMAGE TYPE CONFLICTS')
            command('STAT '+prefixes['h']+rejected+'.PRG','NOT FOUND')
            c['event'](case='ultimate-image-replace-type-rename-self-alias-type-conflict',result='PASS')
            # Reopen the saved image before exporting its new logical files.
            self.image_guard();command('DISMOUNT 10.1:/ --force','OK')
            self.maybe_mounted=False;self.guard('d','after-unmount')
            self.maybe_mounted=True;command('MOUNT '+self.image_path+' --force','LAST MOUNTED BY READYFS')
            self.image_guard()
            for src,dst,kind in pairs:
                if src=='d':command('STAT '+path(src,make_leaf('bm',src,dst,kind)),'NOT FOUND')
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
            # Exit embedded DOS contexts before independently downloading the image.
            command('COMPARE @LAB:/SOURCE/README.SEQ @LAB:/SOURCE/README.SEQ','VERIFY: IDENTICAL')
            raw=io.BytesIO()
            with self.owned.ftp() as ftp:ftp.retrbinary('RETR '+self.owned.root+'/ud-image.d64',raw.write)
            persisted=self.out/'ud-image-after.d64';persisted.write_bytes(raw.getvalue())
            assert persisted.stat().st_size==174848
            listing=subprocess.check_output(['c1541','-attach',str(persisted),'-list']).decode(errors='replace')
            (self.out/'ud-image-directory.txt').write_text(listing)
            assert 'bm-' not in listing.lower()
            assert not re.search(r'"(?:rft[0-9a-f]+|'+replacement+'|'+rejected+r')"',listing.lower())
            for cbm,kind,data in [('owner','s',owner_file.read_bytes()),('hello','p',payload),('note','s',note_file.read_bytes()),('data','u',data_file.read_bytes())]:
                export=self.out/('ud-image-original-'+cbm+'.bin')
                subprocess.run(['c1541','-attach',str(persisted),'-read',cbm+','+kind,str(export)],check=True,capture_output=True)
                assert export.read_bytes()==data,cbm
            for name,(endpoint,data) in targets.items():
                if endpoint!='h':continue
                cbm,extension=name.rsplit('.',1);kind=next(k for k,v in IMAGE_TYPES.items() if v==extension);export=self.out/('ud-image-'+cbm+'.'+extension)
                subprocess.run(['c1541','-attach',str(persisted),'-read',cbm+','+kind,str(export)],check=True,capture_output=True)
                assert export.read_bytes()==data,name
            c['event'](case='ultimate-contained-image-seq-prg-usr-independent-bytes-types-removal',result='PASS')
            c['event'](case='sd-image-matrix-independent-host-bytes',result='PASS')
        finally:
            if self.maybe_mounted:
                assert self.idle, 'Native command still active; cleanup not confirmed'
                # Only a successful exact image-marker comparison authorizes BACK.
                self.image_guard();command('DISMOUNT 10.1:/ --force','OK')
                self.maybe_mounted=False;self.guard('d','final-fat')
                command('IEC 10: PARTITION 1','FAT OR DNP')
                self.fat_verified=True
        fat_leaf='br'+suffix+'.prg'
        fat_target=self.sd_prefix+'out/'+fat_leaf
        command('STAT '+fat_target,'NOT FOUND')
        self.guard('d',fat_leaf);command('COPY @LAB:/IMAGE-TO-FAT.PRG '+fat_target,'COPIED')
        command('COMPARE @LAB:/IMAGE-TO-FAT.PRG '+fat_target,'VERIFY: IDENTICAL')
        self.owned.guard(self.owned.root+'/fat-bridge-oracle.prg')
        command('COPY '+fat_target+' @LAB:/FAT-BRIDGE-ORACLE.PRG','COPIED')
        snapshot=self.owned.snapshot();c['save_json']('native-same-device-bridge-snapshot.json',snapshot)
        for leaf,data in [('fat-to-image.seq',bridge_seed),('image-to-fat.prg',payload),('fat-bridge-oracle.prg',payload)]:
            assert snapshot[leaf]['sha256']==hashlib.sha256(data).hexdigest(),leaf
        c['event'](case='sd-fat-to-own-image-and-back-via-explicit-intermediate',result='PASS')

    def image_guard(self):
        self.owned.guard(self.owned.root+'/sdowner.seq')
        self.command('COMPARE 10.1:/OWNER @LAB:/SDOWNER.SEQ','VERIFY: IDENTICAL')

    def restore(self):
        assert getattr(self,'idle',True),'Native command still active; do not run restoration PRGs'
        assert not getattr(self,'maybe_mounted',False),'Native SD image restoration unconfirmed'
        assert getattr(self,'fat_verified',False),'Native FAT owner restoration unconfirmed'
        super().restore()
