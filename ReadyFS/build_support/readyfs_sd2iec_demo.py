"""Recorded SD2IEC walkthrough; all changes stay in marker-owned fixtures."""
import hashlib, io, json, os, re, subprocess, time
from pathlib import Path
from readyfs_sd2iec_baseline import Baseline

class Sd2iecDemo(Baseline):
    def hidden(self,text,needle=None):
        c=self.c; assert self.idle
        self.idle=False
        c['event'](hidden_command=text)
        c['keys'](text,False);c['keys']([13],False);c['wait_ready'](2,timeout=240)
        self.idle=True
        if needle:c['check']('guard-'+str(self.sequence),needle)
        self.sequence+=1

    def command(self,text,needle=None,explanation='',pages=False):
        c=self.c;assert self.idle
        self.hidden('CLEAR')
        self.idle=False;start=time.time();c['event'](command=text)
        c['keys'](text);time.sleep(.45);typed=time.time();c['keys']([13],False)
        c['wait_ready'](3,timeout=240);self.idle=True
        earlier=[]
        for number in range(24):
            screen=c['capture']('current-demo')
            if '-- MORE --' not in screen.upper():break
            assert pages,'Unexpected paging'
            name=f'preview-{len(c["steps"])+1:02d}-{number+1:02d}.png'
            c['snapshot_png'](name);earlier.append({'screenshot':name,'screen':screen})
            time.sleep(4);self.idle=False;c['keys'](' ',False);c['wait_ready'](3,timeout=240);self.idle=True
        else:raise AssertionError('Too many pages')
        if needle:c['check']('demo-'+str(len(c['steps'])+1).zfill(2),needle)
        c['record_step'](text,explanation=explanation,started=start)
        step=c['steps'][-1];step['typed_epoch']=typed
        if earlier:step['pages']=earlier
        time.sleep(4)
        step['end_epoch']=time.time()

    def fat_guard(self):
        self.owned.guard(self.owned.root+'/sdowner.seq')
        self.hidden('COMPARE '+self.sd_prefix+'OWNER @LAB:/SDOWNER.SEQ','VERIFY: IDENTICAL')

    def image_guard(self):
        assert self.maybe_mounted
        self.hidden('COMPARE 10.1:/OWNER @LAB:/SDOWNER.SEQ','VERIFY: IDENTICAL')

    def native_write(self,text,needle,explanation):
        self.fat_guard();self.command(text,needle,explanation)

    def run(self):
        c=self.c;assert self.sd and self.sd_prefix.startswith('10.1:/')
        self.idle=True;self.maybe_mounted=False;self.fat_verified=True;self.sequence=0
        c['speed'](1)
        # Source is an already independently checked, owned SD D64.
        prior=Path(os.environ['READYFS_SD2IEC_IMAGE_RUN']).resolve()
        assert prior.parent==(c['ROOT']/'logs/readyfs_c64u').resolve()
        ev=[json.loads(x) for x in (prior/'events.jsonl').read_text().splitlines()]
        assert ev[-1].get('complete') and ev[-1].get('restored') and ev[-1]['result']=='PASS'
        scope=json.loads((prior/'continued-native-image.json').read_text())['scope']
        assert scope['owner']==self.sd['marker']
        self.image=scope['path'];assert re.fullmatch(re.escape(self.sd_prefix)+r'out/i[0-9]{10}\.d64',self.image)
        stamp=time.strftime('%H%M%S',time.gmtime());self.work=self.sd_prefix+'out/v'+stamp
        self.names=['V'+stamp+'A','V'+stamp+'B'];prgname='V'+stamp+'P'
        c['save_json']('sd-demo-scope.json',{'native_root':self.work,'image':self.image,'new_image_names':self.names+[prgname],'owner':self.sd['marker']})
        for leaf,data in [('sdowner.seq',self.sd['marker'].upper().encode('ascii'))]:
            self.owned.guard(self.owned.root+'/'+leaf)
            with self.owned.ftp() as ftp:ftp.storbinary('STOR '+self.owned.root+'/'+leaf,io.BytesIO(data))
        # An unmounted Ultimate image, completely separate from boot drive B9.
        hello=b'\x01\x08'+bytes((i*13+7)&255 for i in range(513))
        (self.out/'hello.prg').write_bytes(hello);(self.out/'owner.seq').write_bytes(self.sd['marker'].upper().encode())
        subprocess.run(['c1541','-format','sd demo,rf','d64',str(self.out/'host.d64'),'-write',str(self.out/'hello.prg'),'hello,p','-write',str(self.out/'owner.seq'),'owner,s'],check=True,capture_output=True)
        self.owned.guard(self.owned.root+'/host.d64')
        with self.owned.ftp() as ftp:ftp.storbinary('STOR '+self.owned.root+'/host.d64',io.BytesIO((self.out/'host.d64').read_bytes()))
        self.hidden('AL LAB u:'+self.owned.root,'ALIAS SET')
        self.fat_guard();self.hidden('STAT '+self.work,'NOT FOUND')
        c['chapter']('01 · Find the SD2IEC','Device, partition and folder are separate choices.')
        self.command('PROBE IEC 10:','SD2IEC','Detect the attached SD2IEC through native IEC.')
        self.command('IEC 10: CONFIG','E01','Inspect settings without changing or saving them.')
        self.command('IEC 10: PARTITION 1','FAT OR DNP','The partition reply distinguishes mounted flat images from FAT/DNP.')
        self.native_write('MKDIR '+self.work,'DIRECTORY CREATED','Create a fresh folder inside the owned SD test root.')
        self.command('ALIAS CARD '+self.work,'ALIAS SET','CARD names this SD folder; it does not change its capabilities.')
        c['chapter']('02 · Copy a nested tree','Five files, three subfolders, one recursive copy.')
        self.command('TREE @LAB:/SOURCE','TREE DONE','Five source files span alpha, beta and beta/deep.',True)
        self.native_write('MD @CARD:/TREE','DIRECTORY CREATED','Prepare the destination container.')
        self.fat_guard();self.command('COPY @LAB:/SOURCE @CARD:/TREE -R -W','WHATIF: NO FILES CHANGED','Preview every selected file and folder without writing.',True)
        self.hidden('STAT @CARD:/TREE/README','NOT FOUND')
        self.native_write('COPY @LAB:/SOURCE @CARD:/TREE --recursive','FAIL 0','Copy the complete tree; destination verification is enabled.')
        self.command('TREE @CARD:/TREE','TREE DONE','The SD destination keeps the nested layout.',True)
        for leaf in self.owned.seed:self.hidden('COMPARE @CARD:/TREE/'+leaf.removesuffix('.seq')+' @LAB:/SOURCE/'+leaf,'VERIFY: IDENTICAL')
        c['event'](case='sd-demo-five-native-files-identical',result='PASS')
        c['chapter']('03 · Bring the tree back','Copy SD folders back to Ultimate storage.')
        self.owned.guard(self.owned.root+'/returned');self.command('MKDIR @LAB:/RETURNED','DIRECTORY CREATED','Create a separate host destination for the return copy.')
        self.owned.guard(self.owned.root+'/returned');self.command('CP @CARD:/TREE @LAB:/RETURNED -R','FAIL 0','The short CP and -R forms copy all five files back.')
        self.command('TREE @LAB:/RETURNED','TREE DONE','Read the returned tree; SD logical names can omit type suffixes.',True)
        snap=self.owned.snapshot()
        for leaf,data in self.owned.seed.items():assert snap['returned/'+leaf.removesuffix('.seq')]['sha256']==hashlib.sha256(data).hexdigest()
        c['save_json']('sd-demo-returned-bytes.json',snap);c['event'](case='sd-demo-five-returned-independent-hashes',result='PASS')
        c['chapter']('04 · Other IEC endpoints','Select two files when the destination is flat.')
        self.touched_soft=True
        soft='s0:'+self.owned.root.removeprefix('/USB1')+'/'
        self.command('AL SOFT '+soft,'ALIAS SET','SoftwareIEC is a mapped endpoint, separate from SD2IEC.')
        disk_expected={}
        for leaf,name in zip(('one','two'),self.names):
            c['guard_disk']();self.command('COPY @CARD:/TREE/ALPHA/'+leaf+' 9:/'+name,'COPIED','Copy a chosen nested file into the flat IEC image.')
            data=self.owned.seed['alpha/'+leaf+'.seq'];disk_expected[name.lower()]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            self.owned.guard(self.owned.root+'/'+name.lower()+'.seq');self.command('CP @CARD:/TREE/ALPHA/'+leaf+' @SOFT:/'+name,'COPIED','Copy the same chosen file through SoftwareIEC.')
        c['save_json']('baseline-expected-iec-files.json',disk_expected)
        snap=self.owned.snapshot()
        for leaf,name in zip(('one','two'),self.names):assert snap[name.lower()+'.seq']['sha256']==hashlib.sha256(self.owned.seed['alpha/'+leaf+'.seq']).hexdigest()
        c['event'](case='sd-demo-two-softiec-independent-hashes',result='PASS')
        c['chapter']('05 · Open an SD disk image','Mount first; then address files through device 10.')
        self.fat_guard();self.maybe_mounted=True;self.fat_verified=False
        self.command('MOUNT '+self.image+' --force','LAST MOUNTED BY READYFS','Mount only the owned test image; device 10 now shows its contents.')
        self.command('IEC 10: PARTITION 1','TYPE $02','The native reply confirms the mounted D64 view.')
        self.image_guard()
        self.command('DIR 10.1:/','BLOCKS FREE','Inspect the actual disk-image directory.',True)
        for name in self.names+[prgname]:self.hidden('STAT 10.1:/'+name,'NOT FOUND')
        c['chapter']('06 · Copy inside both images','SD mounts and Ultimate slash paths work differently.')
        for leaf,name in zip(('one','two'),self.names):
            self.image_guard();self.command('COPY @LAB:/RETURNED/ALPHA/'+leaf+' 10.1:/'+name,'COPIED','Use the host return copy while the SD FAT folder is unavailable.')
            self.owned.guard(self.owned.root+'/host.d64');self.command('CP 10.1:/'+name+' @LAB:/HOST.D64/'+leaf+'.SEQ','COPIED','Write directly inside the separate, unmounted Ultimate D64.')
        self.image_guard();self.command('COPY @LAB:/HOST.D64/HELLO.PRG 10.1:/'+prgname,'COPIED','Reverse the direction and preserve the PRG type.')
        self.command('STAT 10.1:/'+prgname,'TYPE: $11','The native directory reports PRG, not just matching bytes.')
        self.owned.guard(self.owned.root+'/fromimg.prg');self.command('COPY 10.1:/'+prgname+' @LAB:/FROMIMG.PRG','COPIED','Save an intermediate file before returning to SD folders.')
        for leaf,name in zip(('one','two'),self.names):self.hidden('COMPARE 10.1:/'+name+' @LAB:/SOURCE/ALPHA/'+leaf+'.SEQ','VERIFY: IDENTICAL')
        c['chapter']('07 · Return to SD folders','Close image access before copying back onto SD.')
        self.image_guard();self.command('DISMOUNT 10.1:/ --force','OK','Return partition 1 to its FAT directory view.')
        self.maybe_mounted=False;self.fat_guard();self.fat_verified=True
        self.native_write('COPY @LAB:/FROMIMG.PRG @CARD:/FROMIMG.PRG','COPIED','Complete image-to-SD-folder transfer through the intermediate host file.')
        self.command('COMPARE @CARD:/FROMIMG.PRG @LAB:/HOST.D64/HELLO.PRG','VERIFY: IDENTICAL','Both image styles and the final SD file contain the same PRG bytes.')
        self.command('IEC 10: CONFIG','E01','Configuration is unchanged; no EEPROM save was needed.')
        snap=self.owned.snapshot();assert snap['fromimg.prg']['sha256']==hashlib.sha256(hello).hexdigest()
        image=io.BytesIO()
        with self.owned.ftp() as ftp:ftp.retrbinary('RETR '+self.owned.root+'/host.d64',image.write)
        (self.out/'host-after.d64').write_bytes(image.getvalue())
        for leaf in ('one','two'):
            dest=self.out/(leaf+'.seq');subprocess.run(['c1541','-attach',str(self.out/'host-after.d64'),'-read',leaf+',s',str(dest)],check=True,capture_output=True)
            assert dest.read_bytes()==self.owned.seed['alpha/'+leaf+'.seq']
        c['event'](case='sd-demo-contained-image-independent-bytes-types',result='PASS')
        self.fat_guard();self.hidden('COMPARE '+self.sd_prefix+'IN/SEED '+self.sd_prefix+'IN/SEED','VERIFY: IDENTICAL')

    def restore(self):
        assert self.idle,'Native command unresolved; do not inject recovery'
        if self.maybe_mounted:
            self.image_guard()
            self.hidden('DISMOUNT 10.1:/ --force','OK')
            self.maybe_mounted=False
            self.fat_guard();self.fat_verified=True
        assert self.fat_verified,'Native FAT return unconfirmed'
        super().restore()
