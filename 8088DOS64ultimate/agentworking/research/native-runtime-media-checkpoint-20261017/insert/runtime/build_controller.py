from pathlib import Path
import os,sys,argparse
P=Path(__file__).resolve().parent;C=P/'controller';sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-controller-build');assert not Path(sys.pycache_prefix).exists()
import json,hashlib,zlib,subprocess,shutil
ap=argparse.ArgumentParser();ap.add_argument('--role',choices=['unit','runtime'],default='unit');role=ap.parse_args().role
S=lambda p:{l.split()[2].lstrip('.'):int(l.split()[1],16)for l in p.read_text().splitlines()if l.startswith('al ')}
N=S(P/('work/build/dos64.labels'if role=='runtime'else'work/build/dos64-tests.labels'));B=S(P/'broker/broker.labels');T=S(P/'phase/transaction-wire.labels');M=S(P/'phase/modal-save.labels');Q=S(P/'phase/runtime-plan.labels')
I=S(P/'worker/incoming.labels')
(C/'native.inc').write_text(''.join(n+'=$%04x\n'%v for n,v in N.items()if n.startswith(('dos64_','hdb_','hd_','hdc_','sav_')))+''.join(n+'=$%04x\n'%v for n,v in B.items()if n.startswith(('modal_','saved_'))))
worker={n:n for n in ['tw_drive','tw_take_sequence','tw_begin','tw_poll','tw_state','tw_error','tw_closed','tw_committing','tw_home','tw_sequence','tw_limit','tw_mode','tw_cancel']}
worker.update({n:n for n in ['ms_begin','ms_poll','ms_state','ms_error','ms_drive','ms_path','ms_cancel']})
lines=[]
for names,table in [(list(worker),dict(T,**M))]:
 for n in names:lines.extend(['.export _'+n,n+'=$%04x'%table[n],'_'+n+'='+n])
lines+=['.export _mw_init,_mw_build','mw_init=$7dd0','mw_build=$7dfc','_mw_init=mw_init','_mw_build=mw_build']
for n in ['mp_drive','mp_readonly','mp_sequence','mp_capacity','mp_image_path','mp_snapshot','mp_image_crc']:
 lines+=['.export _'+n,n+'=$%04x'%Q['_'+n],'_'+n+'='+n]
for n in ['iw_begin','iw_poll','iw_state','iw_error','iw_closed','iw_take','iw_path','iw_limit','iw_enable','iw_cancel']:
 lines+=['.export _'+n,'_'+n+'=$%04x'%I[n]]
for name,native in [('ac_fq','dos64_floppy_request'),('ac_stage_active','dos64_floppy_stage_active'),('ac_disk_a','dos64_disk_reu_base'),('ac_disk_b','dos64_disk_b_descriptor')]:lines+=['.export _'+name,'_'+name+'=$%04x'%N[native]]
(C/'worker.inc').write_text('\n'.join(lines)+'\n')
body=bytearray(57344);records=[];cursor=0x5800
parts=[('phase/transaction-wire.prg',0,0xa000,0),('phase/modal-save.prg',0,0x2900,0),('phase/runtime-plan.prg',1,0x3300,0x4600),('binding/binding.prg',2,0x8000,0x5200),('worker/incoming.prg',0,0x4700,0),('insert-binding/binding.prg',3,0xb800,0x5300)]
def source(off):return 0x3da000+off if off<0x6000 else 0x3f0000+(off-0x6000)
def place(name,offset):
 b=(P/name).read_bytes();payload=b[2:];end=offset+len(payload);assert payload and end<=len(body)and(offset>=0x6000 or end<=0x6000),(name,offset,end);body[offset:end]=payload
 return {'file':name,'host':int.from_bytes(b[:2],'little'),'reu':source(offset),'bytes':len(payload),'crc':zlib.crc32(payload),'logical_offset':offset}
occupied=[]
for i,(name,wrapper,offset,wrapper_offset)in enumerate(parts):
 v=place(name,offset);labels=S((P/name).with_suffix('.labels'));occupied.append((offset,offset+v['bytes'],name))
 line=next(l.split()for l in(P/name).with_suffix('.map').read_text().split('Segment list:')[1].split('Exports list')[0].splitlines()if l.split()and l.split()[0]=='BSS')
 v.update(bss=int(line[1],16),bss_bytes=int(line[3],16),wrapper_reu=0,wrapper_bytes=0,wrapper_crc=0,aux_reu=0,aux_bytes=0,aux_crc=0)
 if wrapper:
  wname={1:'phase/worker-calls.prg',2:'binding/binding-calls.prg',3:'insert-binding/insert-calls.prg'}[wrapper];w=place(wname,wrapper_offset);assert w['host']==0x7dd0
  v.update(wrapper_reu=w['reu'],wrapper_bytes=w['bytes'],wrapper_crc=w['crc']);occupied.append((wrapper_offset,wrapper_offset+w['bytes'],wname))
 if i==5:
  a=place('insert-binding/insert-support.prg',0x5400);assert a['host']==0x6600 and a['bytes']<=0x700
  v.update(aux_reu=a['reu'],aux_bytes=a['bytes'],aux_crc=a['crc']);occupied.append((0x5400,0x5400+a['bytes'],'insert-support'))
 records.append(v)
assert cursor<=0x6000
for (a,b,n),(c,d,m)in zip(sorted(occupied),sorted(occupied)[1:]):assert b<=c,(n,m,hex(b),hex(c))
header='''struct ac_asset {ac_u16 host;ac_u32 reu;ac_u16 bytes;ac_u32 crc;ac_u16 bss,bss_bytes;ac_u32 wrapper_reu;ac_u16 wrapper_bytes;ac_u32 wrapper_crc;ac_u32 aux_reu;ac_u16 aux_bytes;ac_u32 aux_crc;};\nstatic const struct ac_asset ac_assets[6]={\n'''
for r in records:header+='{'+','.join(str(r[k])+('UL'if k in ['reu','crc','wrapper_reu','wrapper_crc','aux_reu','aux_crc']else'u')for k in ['host','reu','bytes','crc','bss','bss_bytes','wrapper_reu','wrapper_bytes','wrapper_crc','aux_reu','aux_bytes','aux_crc'])+'},\n'
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
(P/'WORKERS.MNU').write_bytes(body);(P/'CONTROLLER_BUILD.json').write_text(json.dumps({'records':records,'core_end':cursor,'role':role,'controller_sha256':hashlib.sha256(a).hexdigest(),'controller_bytes':len(a),'commands':commands,'scope':'provisional unit role/controller+exactworker payloads, not nativeUI or finalcontainer'},indent=2)+'\n');print('Controller linked',len(a),hashlib.sha256(a).hexdigest()[:8],'coreend',hex(cursor))
