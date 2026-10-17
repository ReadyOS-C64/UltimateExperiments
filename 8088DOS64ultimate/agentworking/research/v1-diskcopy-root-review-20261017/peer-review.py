from pathlib import Path
import sys,os,json,hashlib,importlib.util,zlib,shutil,struct
P=Path(__file__).resolve().parent;S=P.parent/'native-diskcopy-persistence-final-20261017'
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-review-cache');assert not Path(sys.pycache_prefix).exists()
def ident(q):b=q.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def dump(q,d):q.write_text(json.dumps(d,indent=2)+'\n')
assert ident(S/'MANIFEST.json')['sha256'].startswith('87522cf6')
m=json.loads((S/'MANIFEST.json').read_text());records={}
for n,v in m['files'].items():
 q=S/n;assert ident(q)==v,n;records[str(q)]=v
before=json.loads((S/'closed/INPUTS_BEFORE.json').read_text());assert before==json.loads((S/'closed/INPUTS_AFTER.json').read_text())
for n,v in before.items():
 assert ident(Path(n))==v,n;assert ident(S/'closed/copies'/v['sha256'])==v,n;records[n]=v
products=json.loads((S/'closed/PRODUCTS_BEFORE.json').read_text());assert products==json.loads((S/'closed/PRODUCTS_AFTER.json').read_text())
for n,v in products.items():assert ident(Path(n))==v,n;records[n]=v
for q in [S/'MANIFEST.json',Path(__file__).resolve(),Path(sys.executable).resolve()]:records[str(q)]=ident(q)
dump(P/'INPUTS_BEFORE.json',records)
spec=importlib.util.spec_from_file_location('frozen_inspector',S/'consumer/work/dos_disk_inspect.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
a=(S/'initial/A.IMG').read_bytes();b=(S/'persisted/COPY0001.IMG').read_bytes();assert len(a)==len(b)==368640 and a==b
av=D.Volume(a);bv=D.Volume(b);assert av.payloads==bv.payloads and len(bv.payloads)==37
assert (S/'initial/B.IMG').read_bytes()!=a
for n in ['A.IMG','B.IMG','C.IMG']:
 assert (S/'initial'/n).read_bytes()==(S/'persisted'/n).read_bytes(),n
c=(S/'initial/C.IMG').read_bytes();cv=D.Volume(c[8192:]);assert len(cv.payloads)==112 and cv.payloads['DOS/CONFIG.SYS']==b'c:\r\ndevice=c:\\dos\\ansi.sys\r\nfiles=25\r\nbuffers=25\r\n'
x=(S/'initial/DOS64.CFG').read_bytes();y=(S/'persisted/DOS64.CFG').read_bytes();assert len(x)==len(y)==576;assert zlib.crc32(x[:572])==int.from_bytes(x[572:],'little')and zlib.crc32(y[:572])==int.from_bytes(y[572:],'little')
changes=[i for i,(u,v)in enumerate(zip(x,y))if u!=v];assert all(264<=i<392 or 532<=i<536 or 572<=i<576 for i in changes)
assert y[264:392]==b'/Home/COPY0001.IMG'.ljust(128,b'\0');assert int.from_bytes(y[532:536],'little')==zlib.crc32(b)
assert zlib.crc32(y[:572])!=zlib.crc32(x[:572]);assert zlib.crc32(y)==0x2144df1c
for n in ['DOS64.PRG','DOS64.REL','DOS64.MNU','START.PRG','START.INO','START.RCV','START.RFW']:
 assert (S/'initial'/n).read_bytes()==(S/'persisted'/n).read_bytes(),n
trace=json.loads((S/'run/BIOS_TRACE.json').read_text());fmt=[r for r in trace if r[0]>>8==5];assert len(fmt)==80 and {(r[1]>>8,r[2]>>8)for r in fmt}=={(c,h)for c in range(40)for h in range(2)}
for n in ['DISKCOPY','DISKCOMP']:
 j=json.loads((S/('run/'+n+'.json')).read_text());assert j['passed'];assert j['observations'][-1]['screen'].splitlines()[j['observations'][-1]['cursor'][0]].strip()=='A>'
 assert n!='DISKCOMP'or j['Compare_OK']
for n in ['BOOT','FRESH_BOOT']:
 j=json.loads((S/('run/'+n+'.json')).read_text());assert j['pagination']>0 and all(row[1]for row in j['directory_entries'].values())and j['status'].startswith('PASS_')
# Passive trace source changes only diagnostic vectors/flag, not RAM/replies/guest regs.
bridge=(S/'consumer/work/tests/floppy_export/bridge.cpp').read_text();observer=bridge[bridge.index('    void observe_format()'):bridge.index('    // Explicitly enabled per fixture')];assert 'format_requests.push_back(q)'in observer and 'ram['in observer and 'ram['not in observer.replace('q.regs[i]=uint16_t(ram[format_guest+2*i])|(uint16_t(ram[format_guest+2*i+1])<<8);','')
for n in ['HANDOFF.md','ASSESSMENT.json','PLAN.json','close.py','consumer/work/run_diskcopy.py','consumer/work/tests/floppy_export/bridge.cpp','run/RESULT.json','run/SESSION1.json','closed/RESULT.json']:
 q=P/'evidence'/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/n,q)
for n,v in records.items():assert ident(Path(n))==v,n
dump(P/'INPUTS_AFTER.json',records);dump(P/'RESULT.json',{'status':'PASS_REVIEW_NO_NATIVE_RERUN','subject_pins':len(m['files']),'closed_execution_inputs':len(before),'closed_model_products':products,'all_reviewed_paths':len(records),'all_720_sectors_exact':True,'all_37_FAT_payloads_exact':True,'original_A_B_C_backing_files_exact':True,'C_payloads':len(cv.payloads),'CFG_changed_offsets':changes,'CFG_bodyCRC':hex(zlib.crc32(y[:572])),'CFG_fixed_fullCRC_not_used_as_identity':True,'FORMAT_actual_unique_tracks':len(fmt),'no_new_native_or_device_execution':True,'physical_acceptance':False})
print('PASS',len(m['files']),len(before),len(records))
