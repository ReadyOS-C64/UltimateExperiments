"""Explicit owned native SD image acceptance, Terminal runner only.

The fixture upload explicitly selects XE0, restores exact original settings,
then proves mountability. It does not silently imply general raw-image COPY
support under every extension mode. All roots and images are retained.
"""
import hashlib
import io
import re
import subprocess
import time
from readyfs_sd2iec_baseline import Baseline

class NativeImage(Baseline):
    def run(self):
        c=self.c
        assert self.sd and self.sd_prefix.startswith('10.1:/'), 'Image suite requires verified partition1 bootstrap'
        self.idle=True
        def command(text,needle=None,pause=4):
            assert self.idle, 'Previous operation did not return; do not inject more keys'
            c['command']('CLEAR',pause=1)
            c['event'](command=text)
            c['keys'](text);time.sleep(.65);c['keys']([13]);self.idle=False
            c['wait_ready'](min(pause,4),timeout=3600)
            self.idle=True
            if needle:c['check']('native-image-'+str(len(list(self.out.glob('native-image-*')))).zfill(3),needle)
            return c['capture']('native-image-current')
        self.command=command
        c['speed'](1)
        marker=self.sd['marker'].upper().encode('ascii')
        payload=b'\x01\x08'+bytes((i*13+7)&255 for i in range(513))
        marker_file=self.out/'image-owner.seq';marker_file.write_bytes(marker)
        payload_file=self.out/'image-hello.prg';payload_file.write_bytes(payload)
        image=self.out/'native-source.d64'
        subprocess.run(['c1541','-format','readyfs sd,rf','d64',str(image),
            '-write',str(marker_file),'owner,s','-write',str(payload_file),'hello,p'],check=True,capture_output=True)
        assert image.stat().st_size==174848
        for leaf,data in [('sdowner.seq',marker),('native-source.d64',image.read_bytes()),('image-hello.prg',payload)]:
            self.owned.guard(self.owned.root+'/'+leaf)
            with self.owned.ftp() as ftp:ftp.storbinary('STOR '+self.owned.root+'/'+leaf,io.BytesIO(data))
        self.guard('d','image-fixture')
        name='i'+time.strftime('%m%d%H%M%S',time.gmtime())+'.d64'
        image_path=self.sd_prefix+'out/'+name
        c['save_json']('native-image-scope.json',{'path':image_path,'owner':self.sd['marker'],
            'source_bytes':174848,'source_sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
        screen=command('IEC 10: CONFIG','03,E')
        match=re.search(r'03,E([0-4][0-9A-F])([+-]):\*([+-]):I([0-9A-F]{2}):R[^\n]*',screen)
        assert match,'Cannot restore unknown settings'
        original=match.group(0).strip();extension=int(match[1],16);hidden=match[2]
        assert extension in range(5)
        try:
            command('IEC 10: EXTENSIONS 0','03,E00')
            self.guard('d','image-fixture')
            command('COPY @LAB:/NATIVE-SOURCE.D64 '+image_path,'COPIED')
            command('COMPARE @LAB:/NATIVE-SOURCE.D64 '+image_path,'VERIFY: IDENTICAL')
        finally:
            if self.idle:
                command('IEC 10: EXTENSIONS '+str(extension),'03,E')
                command('IEC 10: HIDE-EXTENSIONS '+('on' if hidden=='+' else 'off'),'03,E')
                restored=command('IEC 10: CONFIG','03,E')
                assert original in restored,'Configuration restore mismatch'
                c['event'](case='native-image-upload-config-restored',result='PASS')
            else:
                c['event'](restore='native configuration',result='UNCONFIRMED',reason='Operation never returned; no further keys injected')
        mounted=False
        try:
            self.guard('d','image-mount')
            command('MOUNT '+image_path+' --force','LAST MOUNTED BY READYFS')
            mounted=True
            command('IEC 10: PARTITION 1','TYPE $02')
            self.image_guard()
            command('DIR 10.1:/','HELLO')
            command('VOLUME 10.1:/','C64 BLOCKS')
            command('COMPARE 10.1:/HELLO @LAB:/IMAGE-HELLO.PRG','VERIFY: IDENTICAL')
            self.owned.guard(self.owned.root+'/image-out.prg')
            command('COPY 10.1:/HELLO @LAB:/IMAGE-OUT.PRG','COPIED')
            self.image_guard()
            command('COPY @LAB:/SOURCE/README.SEQ 10.1:/FROMHOST','COPIED')
            command('COMPARE 10.1:/FROMHOST @LAB:/SOURCE/README.SEQ','VERIFY: IDENTICAL')
            self.image_guard()
            command('COPY @LAB:/SOURCE/README.SEQ 10.1:/MOVEME','COPIED')
            self.image_guard();self.owned.guard(self.owned.root+'/image-moved.seq')
            command('MOVE 10.1:/MOVEME @LAB:/IMAGE-MOVED.SEQ','MOVE COMPLETE')
            command('STAT 10.1:/MOVEME','NOT FOUND')
            self.image_guard()
            command('COPY @LAB:/SOURCE/README.SEQ 10.1:/DELETEME','COPIED')
            self.image_guard();command('DELETE 10.1:/DELETEME --force','DELETED')
            command('STAT 10.1:/DELETEME','NOT FOUND')
            c['event'](case='native-sd-mounted-image-read-write-move-delete',result='PASS')
        finally:
            if mounted and self.idle:
                self.image_guard()
                command('DISMOUNT 10.1:/ --force','OK')
                mounted=False
                self.guard('d','after-unmount')
                command('IEC 10: PARTITION 1','FAT OR DNP')
        self.owned.guard(self.owned.root+'/native-after.d64')
        command('COPY '+image_path+' @LAB:/NATIVE-AFTER.D64','COPIED')
        raw=io.BytesIO()
        with self.owned.ftp() as ftp:ftp.retrbinary('RETR '+self.owned.root+'/native-after.d64',raw.write)
        after=self.out/'native-after.d64';after.write_bytes(raw.getvalue())
        assert after.stat().st_size==174848,'Unexpected wrapper/geometry'
        listing=subprocess.check_output(['c1541','-attach',str(after),'-list']).decode(errors='replace')
        (self.out/'native-persisted-directory.txt').write_text(listing)
        assert '"moveme"' not in listing.lower() and '"deleteme"' not in listing.lower()
        for leaf,kind,data in [('owner','s',marker),('hello','p',payload),('fromhost','s',self.owned.seed['readme.seq'])]:
            target=self.out/('persisted-'+leaf+'.bin')
            subprocess.run(['c1541','-attach',str(after),'-read',leaf+','+kind,str(target)],check=True,capture_output=True)
            assert target.read_bytes()==data,leaf
        snapshot=self.owned.snapshot();c['save_json']('native-image-host-snapshot.json',snapshot)
        assert snapshot['image-out.prg']['sha256']==hashlib.sha256(payload).hexdigest()
        assert snapshot['image-moved.seq']['sha256']==hashlib.sha256(self.owned.seed['readme.seq']).hexdigest()
        c['event'](case='native-image-independent-geometry-bytes-types-source-removal',result='PASS')

    def image_guard(self):
        self.owned.guard(self.owned.root+'/sdowner.seq')
        self.command('COMPARE 10.1:/OWNER @LAB:/SDOWNER.SEQ','VERIFY: IDENTICAL')
