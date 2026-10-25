"""Actual frozen root/C10/C12 candidate admission; only KERNAL/DOS is modeled.

The backend intentionally refuses rather than emulates splat overwrite: the
assertion is stricter, requiring no W-open/CREATE request at all. Native 1581
foreign-slot preservation is a separate gate.
"""
from pathlib import Path
import argparse,hashlib,json
import test_editor_file_integration as integration

TEMP=b'SE~T000000000000'
class Candidates(integration.IntegratedFiles):
    def raw_sectors(self):
        blocks=super().raw_sectors()
        for key,block in tuple(blocks.items()):
            if key[0]!=40 or key[1]<3:continue
            raw=bytearray(block)
            for index in range(8):
                at=index*32
                if raw[at+2] and bytes(raw[at+5:at+21])==TEMP:raw[at+2]=self.foreign_type
            blocks[key]=bytes(raw)
        return blocks

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--frozen',type=Path,required=True)
    frozen=parser.parse_args().frozen.resolve();freeze=json.loads((frozen/'freeze.json').read_text())
    integration.editor_fixture.ROOT=integration.cpu_editor.ROOT=frozen
    integration.editor_fixture.NAMES=integration.cpu_editor.NAMES=freeze['names']
    for name,digest in freeze['assets'].items():
        assert hashlib.sha256((frozen/f'build/overlays/{name}.seo').read_bytes()).hexdigest()==digest
    cases=[]
    for kind in [0x81,0x82,0x01,0xC1,0x84,0x07]:
        for existing in [False,True]:
            f=Candidates()
            try:
                f.foreign_type=kind;f.fs={TEMP:b'FOREIGN RECOVERABLE CONTENT',b'UNCHANGED':b'Other file'}
                if existing:f.fs[b'TARGET']=b'Existing target untouched'
                f.seed_protected();f.start(operation='A');old=f.stable()
                disk={n:bytes(v) for n,v in f.fs.items()};raw=f.raw_sectors();opened=list(f.opens)
                f.enter_name(b'TARGET',True);f.idle(1,3)
                assert f.get('se_f_error',1)==0x93 and f.get('se_f_dos_error',1)==63
                assert f.get('se_io_owned_temp',1)==f.get('se_io_owned_backup',1)==0
                assert f.fs==disk and f.raw_sectors()==raw
                assert not any(name.endswith(b',S,W') for name,_,_ in f.opens[len(opened):])
                assert not any(op==0xC5 for op,_,_ in f.actions)
                assert any(op==0xD2 for op,_,_ in f.actions)
                assert not any(not c.startswith(b'U1:') for c in f.dos_commands)
                f.check_stable(old);f.key(3);f.idle();f.check_stable(old)
                cases.append(dict(type=kind,existing_target=existing,actions=len(f.actions)))
            finally:f.close()
    result=dict(ok=True,cases=cases,prg_sha256=freeze['prg_sha256'],assets=freeze['assets'],
                scope='Actual frozen root/C10/C12; modeled ROM/DOS, no native/physical-media claim')
    (frozen/'candidate-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
