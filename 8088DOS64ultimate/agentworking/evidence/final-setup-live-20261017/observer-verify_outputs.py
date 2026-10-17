"""Independent complete saved-file checks; never communicates with the device."""
from pathlib import Path
import sys,struct,zlib,hashlib,json
P=Path(__file__).resolve().parents[3];sys.path.insert(0,str(P/'tests/setup_installer'))
from dos_disk_inspect import Volume,inspect
sha=lambda b:hashlib.sha256(b).hexdigest()
def verify(directory,release,originals,expected_home=None):
 d=Path(directory);rel=Path(release);cfg=(d/'DOS64.CFG').read_bytes();assert len(cfg)==576 and cfg[:8]==bytes.fromhex('4436344301400200');assert zlib.crc32(cfg[:572])==int.from_bytes(cfg[572:],'little')and zlib.crc32(cfg)==0x2144df1c
 field=lambda at:cfg[at:at+128].split(b'\0')[0].decode('ascii');home=field(8);assert home.startswith('/')
 if expected_home is not None:assert home.casefold()==expected_home.casefold()
 for at,leaf in [(136,'A.IMG'),(264,'B.IMG'),(392,'C.IMG')]:assert field(at)==home+'/'+leaf
 a,b,c=[(d/n).read_bytes()for n in ['A.IMG','B.IMG','C.IMG']];profile=int.from_bytes(cfg[520:524],'little');assert profile in [0,1];geometry=(128,2,16)if profile==0 else(640,4,16);hd=inspect(c,geometry);start,count=struct.unpack_from('<II',c,454);vc=Volume(c[start*512:(start+count)*512]);va,vb=Volume(a),Volume(b);assert len(a)==len(b)==368640 and not vb.payloads
 n=0
 for i,img in enumerate(originals):
  v=Volume(Path(img).read_bytes())
  for name,data in v.payloads.items():assert vc.payloads['DOS/DISK%d/'%(i+1)+name]==data;n+=1
 first=Volume(Path(originals[0]).read_bytes())
 for name in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:assert va.payloads[name]==first.payloads[name]
 assert va.payloads['CONFIG.SYS']==b'FILES=20\r\nBUFFERS=10\r\n'and b'C:\\DOS'in va.payloads['AUTOEXEC.BAT'];assert int.from_bytes(cfg[528:532],'little')==zlib.crc32(a)and int.from_bytes(cfg[532:536],'little')==zlib.crc32(b)
 desc=(rel/'START.REL').read_bytes();tpl=(rel/'START.TPL').read_bytes();assert len(desc)==64 and zlib.crc32(desc[:60])==int.from_bytes(desc[60:],'little')and zlib.crc32(tpl)==int.from_bytes(desc[12:16],'little');at=int.from_bytes(desc[24:28],'little');actual=(d/'START.PRG').read_bytes();assert len(actual)==len(tpl)
 patch=actual[at:at+131];assert patch[0]==0xa5 and int.from_bytes(patch[1:3],'little')in [0xdf1c,0xde1c,0xdffc]and patch[3:]==cfg[8:136];expected=bytearray(tpl);expected[at:at+131]=patch;assert actual==expected
 native=['DOS64.PRG','DOS64.REL','DOS64.MNU','START.INO','START.RCV','START.RFW']
 for name in native:assert (d/name).read_bytes()==(rel/name).read_bytes()
 return {'status':'passed','home':home,'profile':profile,'C_bytes':len(c),'geometry':geometry,'original_DOS_payloads_exact':n,'empty_independent_B':True,'A_boot_payloads_exact':True,'CFG_media_CRCs_exact':True,'START_exact_template_plus_131byte_native_homepatch':True,'all6published_native_assets_exact':True,'C_filesystem':hd,'files':{name:{'bytes':(d/name).stat().st_size,'sha256':sha((d/name).read_bytes())}for name in ['A.IMG','B.IMG','C.IMG','DOS64.CFG','START.PRG',*native]}}
if __name__=='__main__':
 original=sorted((P/'reference').glob('MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - ? of 3.img'));assert len(original)==3;d=P/'agentworking/scratch/v1-final-public-installer-chain-20261017/root-output';release=P/'agentworking/scratch/main-v1-ultimate-stage-20261017/payload';r=verify(d,release,original,'/Home');out=Path(__file__).with_name('OUTPUT_VERIFIER_MODEL_SMOKE.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ['status','original_DOS_payloads_exact','C_bytes','START_exact_template_plus_131byte_native_homepatch']}))
