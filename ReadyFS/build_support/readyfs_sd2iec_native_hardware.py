"""Owned native SD directory/recursive acceptance for the Terminal v3 runner.

Requires bootstrap evidence, exact native owner proof before each mutation, and
an additional unique child below OUT. No existing fixture is moved or removed.
"""
import hashlib
import io
import time
from readyfs_sd2iec_baseline import Baseline

class NativeDirectories(Baseline):
    def run(self):
        c=self.c
        assert self.sd, 'Native suite requires completed owned SD bootstrap'
        def command(text, needle=None, pause=4):
            c['command']('CLEAR',pause=1)
            c['command'](text,needle,pause)
        self.command=command
        c['speed'](1)
        marker_path=self.owned.root+'/sdowner.seq'
        self.owned.guard(marker_path)
        with self.owned.ftp() as ftp:
            ftp.storbinary('STOR '+marker_path,io.BytesIO(self.sd['marker'].upper().encode('ascii')))
        # First native directory request deliberately precedes any PROBE.
        unqualified='10:/'+self.sd['root']+'/'
        command('DIR '+unqualified+'in/','SEED')
        command('PROFILE IEC 10:','SD2IEC')
        command('VOLUME '+self.sd_prefix+'in/','C64 BLOCKS')
        command('VOLUME @LAB:/SOURCE','RAW PATH:')
        command('VOLUME 9:/','C64 BLOCKS')
        command('TREE '+unqualified+'tree/','INNER')
        child='n'+time.strftime('%m%d%H%M%S',time.gmtime())
        self.work=self.sd_prefix+'out/'+child
        c['save_json']('native-directory-scope.json',{'root':self.work,'marker':self.sd['marker'],
            'policy':'Preserve root/source; only delete explicitly created descendants'})
        self.mutate('MD '+self.work,'DIRECTORY CREATED',self.work)
        command('AL CARD '+self.work,'ALIAS SET')
        self.mutate('MD @CARD:/single','DIRECTORY CREATED',self.work+'/single')
        self.mutate('COPY '+self.sd_prefix+'in/seed @CARD:/single/original','COPIED',self.work+'/single/original')
        self.mutate('RENAME @CARD:/single/original @CARD:/single/renamed','RENAME COMPLETE',self.work+'/single/original',self.work+'/single/renamed')
        command('COMPARE @CARD:/single/renamed '+self.sd_prefix+'in/seed','VERIFY: IDENTICAL')
        self.mutate('DELETE @CARD:/single/renamed --force','DELETED',self.work+'/single/renamed')
        self.mutate('RD @CARD:/single --force','DIRECTORY REMOVED',self.work+'/single')
        command('STAT @CARD:/single','NOT FOUND')
        c['event'](case='native-folder-create-rename-scratch-remove',result='PASS')
        self.mutate('MD @CARD:/copied','DIRECTORY CREATED',self.work+'/copied')
        self.mutate('COPY @LAB:/SOURCE @CARD:/copied --recursive','FAIL 0',self.work+'/copied')
        command('TREE @CARD:/copied','TREE DONE')
        self.verify_tree('copied')
        self.mutate('MD @CARD:/moved','DIRECTORY CREATED',self.work+'/moved')
        self.mutate('MOVE @CARD:/copied @CARD:/moved -R','FAIL 0',self.work+'/copied',self.work+'/moved')
        self.verify_tree('moved')
        command('TREE @CARD:/copied','TREE DONE')
        # Export through recursive SD source traversal; filenames are logical
        # CBM stems, so compare the independent host oracle without .seq suffix.
        self.owned.guard(self.owned.root+'/sd-oracle')
        command('MD @LAB:/SD-ORACLE','DIRECTORY CREATED')
        self.owned.guard(self.owned.root+'/sd-oracle')
        command('COPY @CARD:/moved @LAB:/SD-ORACLE -R','FAIL 0')
        snapshot=self.owned.snapshot();c['save_json']('native-tree-export-snapshot.json',snapshot)
        for stem,data in self.owned.seed.items():
            key='sd-oracle/'+stem.removesuffix('.seq')
            assert snapshot[key]['sha256']==hashlib.sha256(data).hexdigest(),key
        c['event'](case='native-recursive-independent-host-bytes',result='PASS')
        # What-if must leave every fixture readable and unchanged.
        command('DELETE @CARD:/moved -R -W','DONE W0 D0 M0')
        self.verify_tree('moved')
        self.mutate('DELETE @CARD:/moved -R --force','FAIL 0',self.work+'/moved')
        self.mutate('RD @CARD:/moved --force','DIRECTORY REMOVED',self.work+'/moved')
        self.mutate('RD @CARD:/copied --force','DIRECTORY REMOVED',self.work+'/copied')
        command('STAT @CARD:/moved','NOT FOUND')
        command('STAT @CARD:/copied','NOT FOUND')
        self.guard('d','final')
        command('COMPARE '+self.sd_prefix+'in/seed '+self.sd_prefix+'in/seed','VERIFY: IDENTICAL')
        c['event'](case='native-recursive-copy-move-whatif-delete',result='PASS')
        for mhz in (16,64):
            c['speed'](mhz)
            command('DIR '+unqualified+'in/','SEED')
            command('VOLUME '+self.sd_prefix+'in/','C64 BLOCKS')
            command('COMPARE '+self.sd_prefix+'owner @LAB:/SDOWNER.SEQ','VERIFY: IDENTICAL')
            c['event'](case=f'native-directory-volume-read-{mhz}mhz',result='PASS')
        c['speed'](1)

    def mutate(self,text,needle,*paths):
        assert paths and all(p==self.work or p.startswith(self.work+'/') for p in paths)
        self.guard('d','mutation')
        self.command(text,needle)

    def verify_tree(self,child):
        for stem in self.owned.seed:
            native=stem.removesuffix('.seq')
            self.command('COMPARE @CARD:/'+child+'/'+native+' @LAB:/SOURCE/'+stem,'VERIFY: IDENTICAL')
