"""Actual registered62 large-source/reduced-provider gate, CPU only.

Preserve the released70,002B/70,000B-line four-mode/BOTTOM/Q/Undo oracle.
Add source-aware all62 authentication and only the real NC/SC2 FE reservations.
Read the full16MiB emulator REU; protect every byte beyond the configured
16/32-bank provider during rendering. ROM/source-import fixture seams remain.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,inspect,json,zipfile
import test_cache_capacity_current as original
import test_cache_rebase_registered as registered

ROOT=original.ROOT


class Fixture(original.Fixture):
    def reu(self):
        raw=C.create_string_buffer(16*1024*1024)
        self.dll.gm_reu(self.m.handle,len(raw),raw)
        return raw.raw
    def source(self,data,banks=2,physical=16):
        self.reduced_physical=physical
        return super().source(data,banks,physical)
    def render(self):
        size=getattr(self,'reduced_physical',256)*65536
        before=self.reu()[size:]
        result=super().render()
        assert self.reu()[size:]==before,'render wrote beyond configured physical provider'
        return result


def run(out,fixture,project,banks):
    seal=registered.authenticate(fixture,project)
    with zipfile.ZipFile(fixture/'product-sources.zip')as z:
        assert b'NC_REU=$1500' in z.read('src/render/grid/caret/api.inc')
        assert b'SC_REU=$1600' in z.read('src/render/grid/paragraph/prose2.inc')
    source=inspect.getsource(original.run)
    replacements=[
        ("assert len(identity['names'])==54 and identity['names'][-1]=='line'", "assert len(identity['names'])==62 and identity['names'][-2:]==['parse','xform']"),
        ('else:ranges=[(0,22*240)]','else:ranges=[(0,22*240)]+([(0x1500,0x1680)]if mode in(1,2)else[])'),
    ]
    for old,new in replacements:
        assert source.count(old)==1,('capacity oracle changed',old)
        source=source.replace(old,new)
    namespace=dict(vars(original),Fixture=Fixture)
    exec(compile(source,str(out)+'::registered62-capacity','exec'),namespace)
    result=namespace['run'](out,fixture,banks)
    (out/'executed-capacity.py').write_text(source)
    result.update(registered62_identity=seal,adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),oracle_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),full16MiB_reads=True,provider_tail_guard='Every render preserves all16MiB bytes beyond the configured16/32bank provider; original in-provider FE/newtyped53 checks unchanged',scope=__doc__)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('CAPACITY62_PASS',out,flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--banks',type=int,choices=(16,32),default=16);p.add_argument('--out',type=Path);a=p.parse_args()
    out=a.out or ROOT/'build/cache-rebase-capacity'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print('RUN',out,flush=True);run(out.resolve(),a.fixture.resolve(),a.project.resolve(),a.banks)
