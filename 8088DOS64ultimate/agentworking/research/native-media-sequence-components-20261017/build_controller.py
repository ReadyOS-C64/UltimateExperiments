from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;C=P/'controller';sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-controller-build');assert not Path(sys.pycache_prefix).exists()
import json,hashlib,zlib,subprocess,shutil
S=lambda p:{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
N=S(P/'work/build/dos64-tests.labels');B=S(P/'broker/broker.labels');T=S(P/'phase/transaction-wire.labels');M=S(P/'phase/modal-save.labels');Q=S(P/'phase/runtime-plan.labels')
(C/'native.inc').write_text(''.join(n+'=$%04x\n'%v for n,v in N.items()if n.startswith(('dos64_','hdb_','hd_','hdc_','sav_')))+''.join(n+'=$%04x\n'%v for n,v in B.items()if n.startswith(('modal_','saved_'))))
worker={n:n for n in ['tw_take_sequence','tw_begin','tw_poll','tw_state','tw_error','tw_closed','tw_committing','tw_home','tw_sequence','tw_limit','tw_mode','tw_cancel']}
worker.update({n:n for n in ['ms_begin','ms_poll','ms_state','ms_error','ms_drive','ms_path','ms_cancel']})
lines=[]
for names,table in [(list(worker),dict(T,**M))]:
 for n in names:lines.extend(['.export _'+n,n+'=$%04x'%table[n],'_'+n+'='+n])
lines+=['.export _mw_init,_mw_build','mw_init=$7dd0','mw_build=$7dfc','_mw_init=mw_init','_mw_build=mw_build']
for n in ['mp_drive','mp_readonly','mp_sequence','mp_capacity','mp_image_path','mp_snapshot','mp_image_crc']:
 lines+=['.export _'+n,n+'=$%04x'%Q['_'+n],'_'+n+'='+n]
(C/'worker.inc').write_text('\n'.join(lines)+'\n')
body=bytearray(40960);records=[];cursor=0x2800
parts=[('phase/transaction-wire.prg',0),('phase/modal-save.prg',0),('phase/runtime-plan.prg',1),('binding/binding.prg',2)]
def source(off):return 0x3da000+off if off<0x6000 else 0x3f0000+(off-0x6000)
def place(name,offset):
 b=(P/name).read_bytes();payload=b[2:];body[offset:offset+len(payload)]=payload
 return {'file':name,'host':int.from_bytes(b[:2],'little'),'reu':source(offset),'bytes':len(payload),'crc':zlib.crc32(payload),'logical_offset':offset}
for i,(name,wrapper)in enumerate(parts):
 offset=0x8000 if i==3 else cursor;v=place(name,offset);labels=S((P/name).with_suffix('.labels'))
 line=next(l.split()for l in(P/name).with_suffix('.map').read_text().split('Segment list:')[1].split('Exports list')[0].splitlines()if l.split()and l.split()[0]=='BSS')
 v.update(bss=int(line[1],16),bss_bytes=int(line[3],16),wrapper_reu=0,wrapper_bytes=0,wrapper_crc=0)
 if i<3:cursor=(offset+v['bytes']+255)&~255
 if wrapper:
  wname='phase/worker-calls.prg'if wrapper==1 else'binding/binding-calls.prg';w=place(wname,cursor);assert w['host']==0x7dd0
  v.update(wrapper_reu=w['reu'],wrapper_bytes=w['bytes'],wrapper_crc=w['crc']);cursor=(cursor+w['bytes']+255)&~255
 records.append(v)
assert cursor<=0x6000
header='''struct ac_asset {ac_u16 host;ac_u32 reu;ac_u16 bytes;ac_u32 crc;ac_u16 bss,bss_bytes;ac_u32 wrapper_reu;ac_u16 wrapper_bytes;ac_u32 wrapper_crc;};\nstatic const struct ac_asset ac_assets[4]={\n'''
for r in records:header+='{'+','.join(str(r[k])+('UL'if k in ['reu','crc','wrapper_reu','wrapper_crc']else'u')for k in ['host','reu','bytes','crc','bss','bss_bytes','wrapper_reu','wrapper_bytes','wrapper_crc'])+'},\n'
(C/'action_assets.h').write_text(header+'};\n')
(C/'aliases.s').write_text('.setcpu "6502"\n.include "worker.inc"\n')
for obsolete in [C/'controller.prg',C/'controller.labels',C/'controller.map',P/'WORKERS.MNU',P/'CONTROLLER_BUILD.json']:
 obsolete.unlink(missing_ok=True)
commands=[];tools={n:str(Path(shutil.which(n)).resolve())for n in ['cc65','ca65','ld65']};env=dict(os.environ)
for n in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
def run(a):
 a=list(map(str,a));commands.append(a)
 with(P/('BUILD%02d.stdout'%len(commands))).open('wb')as out,(P/('BUILD%02d.stderr'%len(commands))).open('wb')as err:subprocess.run(a,cwd=C,env=env,stdout=out,stderr=err,check=True)
for name in ['action_shell','action_io']:run([tools['cc65'],'-t','none','-Oirs',name+'.c','-o',name+'.s'])
for name in ['entry','action_shell','action_io','native_calls','aliases']:run([tools['ca65'],'-g',name+'.s','-o',name+'.o'])
run([tools['ld65'],'-C','controller.cfg','-o','controller.prg','-Ln','controller.labels','-m','controller.map','entry.o','action_shell.o','action_io.o','native_calls.o','aliases.o',Path(tools['cc65']).parents[1]/'share/cc65/lib/none.lib'])
a=(C/'controller.prg').read_bytes();assert a[:2]==b'\0\x80'and len(a)-2<=0x1d80;body[0x6000:0x6000+len(a)-2]=a[2:]
(P/'WORKERS.MNU').write_bytes(body);(P/'CONTROLLER_BUILD.json').write_text(json.dumps({'records':records,'core_end':cursor,'controller_sha256':hashlib.sha256(a).hexdigest(),'controller_bytes':len(a),'commands':commands,'scope':'provisional unit role/controller+exactworker payloads, not nativeUI or finalcontainer'},indent=2)+'\n');print('Controller linked',len(a),hashlib.sha256(a).hexdigest()[:8],'coreend',hex(cursor))
