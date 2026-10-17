from history_common import *
for n,ret,args in [('bulk_model_file_count',C.c_uint32,[ptr]),('bulk_model_file_path',C.c_uint32,[ptr,C.c_uint32,ptr,C.c_uint32])]:fn=getattr(L,n);fn.restype=ret;fn.argtypes=args

def files(f):
 out={}
 for i in range(L.bulk_model_file_count(f.m)):
  b=C.create_string_buffer(512);n=L.bulk_model_file_path(f.m,i,b,512);assert 0<n<128;name=b.raw[:n];assert name not in out and name.startswith(b'/');out[name]=model_file(f,name)
 assert len(out)==L.bulk_model_file_count(f.m);return out

def archive_all(name,remote):
 d=ROOT/name;d.mkdir();rows={}
 for path,body in remote.items():
  h=sha(body);p=d/(h+'.bin')
  if not p.exists():p.write_bytes(body)
  rows[path.decode('ascii')]={'sha256':h,'bytes':len(body),'content':p.name}
 (d/'REMOTE_FILES.json').write_text(json.dumps(rows,sort_keys=True,indent=2)+'\n');return rows
f=None
try:
 f=Menu();m=f.m;before_remote=files(f);assert not any(b'/S0001.'in n or b'/B0001.'in n for n in before_remote);lane=boot(f);go,press=menu(f,lane);press(ord('b'));press(ord('s'),1600000000)
 assert(L.dos64_peek(m,BR['br_success']),L.dos64_peek(m,BR['br_error']))==(1,0);r1=files(f);p1=f.home+b'/B0001.IMG';assert r1[p1]==f.b;cfg1=r1[f.home+b'/DOS64.CFG'];assert cfg1[264:392]==p1.ljust(128,b'\0');assert f.reu(0x3ff020,576)==cfg1
 a1=f.home+b'/S0001.OLD';j1=f.home+b'/S0001.JRN';assert r1[a1]==f.config and len(r1[j1])==1284;assert not any(n in r1 for n in[f.home+b'/DOS64.JRN',f.home+b'/DOS64.OLD',f.home+b'/DOS64.NEW'])
 for n,b in before_remote.items():
  if n!=f.home+b'/DOS64.CFG':assert r1[n]==b,n
 finish(f,go,press);r1closed=files(f);assert r1closed==r1;archive_all('after-first-Finish',r1closed)
 active=ROOT/'restart';active.mkdir()
 for p in(ROOT/'initial').iterdir():
  if p.is_file():shutil.copyfile(p,active/p.name)
 for path,b in r1closed.items():
  # Local mirrors are only convenience inputs for the START fixture; exact
  # original remote paths, including all archives, are subsequently seeded.
  if path.startswith(f.home+b'/')and b'/'not in path[len(f.home)+1:]:(active/path.decode().split('/')[-1]).write_bytes(b)
 f.close();f=None;os.environ['PUBLISHED_DIRECTORY']=str(active);os.environ['MEDIA_DIRECTORY']=str(active);f=Menu();m=f.m
 for n,b in r1closed.items():L.bulk_model_seed(m,n,b,len(b))
 assert files(f)==r1closed,'every created remote artifact must survive restart';archive_all('fresh-before-SYS',files(f));lane=boot(f);assert f.b_path==p1 and f.b==r1[p1] and f.reu(0x180000,368640)==r1[p1];go,press=menu(f,lane);press(ord('b'));press(ord('s'),1600000000)
 assert(L.dos64_peek(m,BR['br_success']),L.dos64_peek(m,BR['br_error']))==(1,0);r2=files(f);p2=f.home+b'/B0002.IMG';a2=f.home+b'/S0002.OLD';j2=f.home+b'/S0002.JRN';assert r2[p2]==r1[p1] and r2[a2]==cfg1 and len(r2[j2])==1284;cfg2=r2[f.home+b'/DOS64.CFG'];assert cfg2[264:392]==p2.ljust(128,b'\0')and f.reu(0x3ff020,576)==cfg2
 for n,b in r1closed.items():
  if n!=f.home+b'/DOS64.CFG':assert r2[n]==b,n
 assert r2[a1]==r1[a1]and r2[j1]==r1[j1]and r2[p1]==r1[p1];assert not any(n in r2 for n in[f.home+b'/DOS64.JRN',f.home+b'/DOS64.OLD',f.home+b'/DOS64.NEW']);finish(f,go,press);assert files(f)==r2;archive_all('after-second-Finish',r2)
 save('RESULT.json',{'passed':True,'runtime_sha256':sha(f.main),'actual_START_CIA_ordinaryS_Finish_twice':True,'fresh_machine_all_remote_files_byte_exact_before_SYS':True,'first_sequence':1,'fresh_selected_sequence':2,'all_sequence1_images_archives_preserved':True,'first_file_count':len(r1),'second_file_count':len(r2),'originals_exact':True,'seconds':time.monotonic()-start,'scope':'actual old0bfa coldnative/realCIA and independent allfileoracle; no guestDOS/physical/FDISKclaim'})
 print('PASS',time.monotonic()-start,flush=True)
except BaseException as e:
 save('FAILURE.json',{'type':type(e).__name__,'error':repr(e),'seconds':time.monotonic()-start,'native':get(f.m,'dos64_native_diag',19).hex()if f else None});raise
finally:
 if f:f.close()
