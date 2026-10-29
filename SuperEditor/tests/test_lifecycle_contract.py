"""Preparatory lifecycle acceptance contract, NOT an implemented resume adapter.

Default tests exercise a proposed two-extent record and reject-before-write
rules on a host model. --product-profile runs actual frozen6510 allocation
services to check reduced-REU headroom; it does not simulate a successful
product suspend, call ReadyOS, or change production files.
"""
from pathlib import Path
import argparse,binascii,json,struct,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
EXTENTS=((0x1000,0xB600),(0xCA00,0x0600))
ZP=(2,24)
HEADER=0xBC20
OWNER=0xFC  # Proposal only; parent must reserve an unused provider type.
BUSY=('job','phase_owner','doc_busy','read_locks','capture_busy','splice',
      'hot_phase','hot_owned','history_phase','block_phase','clipboard_busy',
      'overlay_R_busy','overlay_C_busy','input_queued')


def crc(data):return binascii.crc_hqx(data,0xFFFF)


def safe_point(state):
    return state.get('running')==1 and state.get('doc_ready')==1 and \
        state.get('ui') in (0,4) and all(state.get(k)==0 for k in BUSY)


def record(ram,binding,epoch,provider,logical=7,physical=19):
    """Draft SEL1 layout. Exact extents are checked rather than trusted input."""
    assert len(ram)==65536 and len(binding)==16 and len(provider)==768
    assert 0<logical<256 and 0<physical<256 and 0<epoch<65536
    bank=bytearray(65536);cursor=0
    for start,length in EXTENTS:
        bank[cursor:cursor+length]=ram[start:start+length];cursor+=length
    bank[cursor:cursor+ZP[1]]=ram[ZP[0]:sum(ZP)];cursor+=ZP[1]
    h=bytearray(64);h[:8]=b'SEL1'+bytes((1,1,2,ZP[1]));h[8:24]=binding
    struct.pack_into('<H',h,24,epoch)
    struct.pack_into('<HHHHHH',h,28,EXTENTS[0][0],EXTENTS[0][1],
        EXTENTS[1][0],EXTENTS[1][1],ZP[0],ZP[1])
    struct.pack_into('<HH',h,40,crc(bank[:cursor]),crc(provider))
    h[44:47]=bytes((logical,physical,OWNER))
    struct.pack_into('<H',h,62,crc(h[:62]))
    bank[HEADER:HEADER+64]=h
    return bytes(bank)


def restore(ram,bank,binding,epoch,provider,logical=7,physical=19):
    """Host specification: validate every byte/identity before first RAM write."""
    if len(bank)!=65536 or len(ram)!=65536:raise ValueError('size')
    h=bank[HEADER:HEADER+64]
    expected=(0x1000,0xB600,0xCA00,0x0600,2,24)
    if h[:8]!=b'SEL1'+bytes((1,1,2,24)):raise ValueError('schema/unpublished')
    if h[8:24]!=binding or struct.unpack_from('<H',h,24)[0]!=epoch:raise ValueError('build/epoch')
    if struct.unpack_from('<6H',h,28)!=expected:raise ValueError('extent')
    if h[44:47]!=bytes((logical,physical,OWNER)):raise ValueError('capability')
    if struct.unpack_from('<H',h,62)[0]!=crc(h[:62]):raise ValueError('header CRC')
    if struct.unpack_from('<H',h,40)[0]!=crc(bank[:0xBC18]):raise ValueError('payload CRC')
    if struct.unpack_from('<H',h,42)[0]!=crc(provider):raise ValueError('provider changed')
    # Commit after complete validation. A real adapter must additionally prove
    # current object tokens/graph and safely execute outside restored extents.
    cursor=0
    for start,length in EXTENTS:
        ram[start:start+length]=bank[cursor:cursor+length];cursor+=length
    ram[2:26]=bank[cursor:cursor+24]


class Contract(unittest.TestCase):
    def setUp(self):
        self.ram=bytearray((i*37+11)&255 for i in range(65536))
        self.binding=bytes(range(16));self.provider=bytes((i*13+7)&255 for i in range(768))
        self.bank=record(self.ram,self.binding,7,self.provider)

    def test_two_extents_CA_settings_and_ZP_restore_only(self):
        current=bytearray((i*19+5)&255 for i in range(65536));before=bytes(current)
        restore(current,self.bank,self.binding,7,self.provider)
        for i in range(65536):
            included=2<=i<26 or any(start<=i<start+length for start,length in EXTENTS)
            self.assertEqual(current[i],self.ram[i] if included else before[i],hex(i))
        self.assertEqual(current[0xCB80:0xCBC0],self.ram[0xCB80:0xCBC0])
        self.assertEqual(current[0xC600:0xCA00],before[0xC600:0xCA00])

    def test_every_header_byte_and_payload_regions_reject_before_write(self):
        offsets=list(range(HEADER,HEADER+64))+[0,0x2FFF,0x4000,0xB5FF,0xB600,0xBBFF,0xBC00,0xBC17]
        for offset in offsets:
            bank=bytearray(self.bank);bank[offset]^=1;current=bytearray(self.ram);before=bytes(current)
            with self.assertRaises(ValueError,msg=hex(offset)):restore(current,bank,self.binding,7,self.provider)
            self.assertEqual(current,before)

    def test_bad_identity_or_foreign_provider_reject_atomically(self):
        cases=[(bytes(16),7,self.provider,7,19),(self.binding,8,self.provider,7,19),
            (self.binding,7,bytes(768),7,19),(self.binding,7,self.provider,8,19),
            (self.binding,7,self.provider,7,20)]
        for binding,epoch,provider,logical,physical in cases:
            current=bytearray(self.ram);before=bytes(current)
            with self.assertRaises(ValueError):restore(current,self.bank,binding,epoch,provider,logical,physical)
            self.assertEqual(current,before)

    def test_safe_point_refuses_every_owned_job_and_does_not_require_flush(self):
        state=dict.fromkeys(BUSY,0);state.update(running=1,doc_ready=1,ui=0,pending=1)
        self.assertTrue(safe_point(state))  # Entire9200..99FF hot gap is saved.
        for key in BUSY:
            candidate=dict(state);candidate[key]=1
            self.assertFalse(safe_point(candidate),key)
        for ui in (1,2,3):self.assertFalse(safe_point(dict(state,ui=ui)))
        self.assertTrue(safe_point(dict(state,ui=4)))

    def test_transfer_geometry_and_snapshot_tail_budget(self):
        self.assertEqual(sum(length for _,length in EXTENTS),0xBC00)
        self.assertLessEqual(HEADER+64,65536)
        self.assertEqual(65536-(HEADER+64),0x43A0)
        for start,length in EXTENTS:
            self.assertTrue(start+length<=0xC600 or start>=0xCA00)
        # Existing ordinaryDMA deliberately cannot do these lifecycle extents.
        self.assertFalse(all(0x4000<=start and start+length<=0xC000 for start,length in EXTENTS))


def product_profile(frozen,out):
    """Real provider/object/catalog allocation; no host capacity simulation."""
    import test_grid_modes as grid
    import font_fixture
    frozen=frozen.resolve();identity=json.loads((frozen/'freeze.json').read_text())
    grid.cpu_editor.ROOT=grid.editor_fixture.ROOT=font_fixture.ROOT=frozen
    grid.cpu_editor.NAMES=grid.editor_fixture.NAMES=identity['names']
    out.mkdir(parents=True,exist_ok=True);dll=grid.runner(out);f=grid.Fixture(out,frozen,dll)
    profiles=[]
    try:
        for banks in (8,16,32):
            f.call('se_clear_state');f.put('se_reu_banks',banks,2)
            stages=[];failed=None
            def call(name,a=0):
                nonlocal failed
                tables=tuple(f.read(f.s[k],256) for k in
                    ('se_reu_map','se_reu_logical_owner','se_reu_physical_owner')) if name=='se_reu_alloc' else None
                reu=f.reu() if tables else None
                regs=f.call(name,a);stages.append(dict(stage=name,a=regs.a,carry=bool(regs.p&1)))
                if regs.p&1:
                    failed=name
                    if tables:
                        assert tables==tuple(f.read(f.s[k],256) for k in
                            ('se_reu_map','se_reu_logical_owner','se_reu_physical_owner'))
                        assert reu==f.reu()
                return not regs.p&1
            for name,a in [('se_reu_provider_init',0),('se_object_init',0),('se_clip_init',0),('se_overlay_init',0),('se_doc_init',1)]:
                if not call(name,a):break
            if not failed:
                from overlays import HEADER as SEO_HEADER
                for name,image in f.assets.items():
                    f.m.load(f.s['se_overlay_header'],image[:SEO_HEADER]);f.m.load(0x5000,image[SEO_HEADER:])
                    if not call('se_overlay_import'):break
            # Exact allocation prefix of actual C28 font-import BEGIN: two FD
            # banks. This checks capacity, not IEC or pack data semantics.
            if not failed:
                for _ in range(2):
                    if not call('se_reu_alloc',0xFD):break
            owners=f.read(f.s['se_reu_physical_owner'],256)
            allocated=[dict(bank=i,owner=v) for i,v in enumerate(owners) if v not in (0,255)]
            profiles.append(dict(physical_banks=banks,minimum_doc_banks=1,failed=failed,stages=stages,allocated=allocated))
            assert f.read(0xC600,1024)==f.shim
        assert profiles[0]['failed']=='se_reu_alloc'
        assert all(not p['failed'] for p in profiles[1:])
        result=dict(status='passed',scope='Actual6510 provider/object/36catalog plus twofont-allocation prefix only; no lifecycle or smallREU editing claim.',identity=identity,profiles=profiles)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='identity'},indent=2))
    finally:f.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--product-profile',action='store_true');parser.add_argument('--fixture',type=Path);parser.add_argument('--out',type=Path,default=ROOT/'build/lifecycle-contract/profile');args,rest=parser.parse_known_args()
    if args.product_profile:
        if not args.fixture:parser.error('--product-profile requires --fixture immutable')
        product_profile(args.fixture,args.out)
    else:unittest.main(argv=[sys.argv[0]]+rest)
