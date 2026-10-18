"""Independent read-only FAT12 oracle; target logic is never reused."""
from pathlib import Path
import hashlib,json,struct
class Fat12:
 def __init__(self,data):
  self.data=data;self.bps,self.spc=struct.unpack_from('<HB',data,11);self.res=struct.unpack_from('<H',data,14)[0];self.nfat=data[16];self.nroot=struct.unpack_from('<H',data,17)[0];self.total=struct.unpack_from('<H',data,19)[0];self.spf=struct.unpack_from('<H',data,22)[0]
  assert len(data)==self.bps*self.total==368640 and self.nfat==2
  self.root_lba=self.res+self.nfat*self.spf;self.root_sectors=(self.nroot*32+self.bps-1)//self.bps;self.data_lba=self.root_lba+self.root_sectors;self.clusters=(self.total-self.data_lba)//self.spc
  self.fat=data[self.res*self.bps:(self.res+self.spf)*self.bps];assert self.fat==data[(self.res+self.spf)*self.bps:(self.res+2*self.spf)*self.bps],'FAT copies differ'
  self.root=self.entries(data[self.root_lba*self.bps:(self.root_lba+self.root_sectors)*self.bps]);self.free=[i for i in range(2,self.clusters+2) if self.value(i)==0]
 def value(self,c):
  p=c+c//2;v=self.fat[p]|self.fat[p+1]<<8;return v>>4 if c&1 else v&4095
 def chain(self,c):
  out=[]
  while c:
   assert 2<=c<self.clusters+2 and c not in out,'invalid or cyclic FAT chain'
   out.append(c);c=self.value(c)
   if c>=0xff8:break
   assert c not in [0,1,0xff7] and c<0xff0,'free/reserved cluster in chain'
  return out
 def cluster(self,c):return self.data[(self.data_lba+(c-2)*self.spc)*self.bps:][:self.spc*self.bps]
 @staticmethod
 def entries(raw):
  out={}
  for off in range(0,len(raw),32):
   e=raw[off:off+32]
   if not e or e[0]==0:break
   if e[0]==0xe5:continue
   name=e[:8].decode('ascii').rstrip();ext=e[8:11].decode('ascii').rstrip();name+=('.'+ext if ext else '')
   assert name not in out,'duplicate live name'
   out[name]={'raw':e,'attr':e[11],'cluster':int.from_bytes(e[26:28],'little'),'size':int.from_bytes(e[28:32],'little')}
  return out
 def content(self,e):return b''.join(self.cluster(c) for c in self.chain(e['cluster']))[:e['size']]
 def directory(self,e):assert e['attr']&16;return self.entries(b''.join(self.cluster(c) for c in self.chain(e['cluster'])))
 def allocated(self):return {i for i in range(2,self.clusters+2) if self.value(i)!=0}
 def assert_original(self,original):
  for name,e in original.root.items():
   assert name in self.root,(name,'original entry missing')
   assert e['raw']==self.root[name]['raw'],(name,'original metadata changed')
   if not e['attr']&24:
    assert self.chain(e['cluster'])==original.chain(e['cluster']),(name,'original FAT chain changed')
    assert self.content(e)==original.content(e),(name,'original data changed')
def verify(directory,source):
 original=Fat12(source);assert len(original.free)*original.bps*original.spc==9216
 report=[]
 expected=original.content(original.root['CONFIG.SYS']);assert expected==b'c:\r\ndevice=c:\\dos\\ansi.sys\r\nfiles=25\r\nbuffers=25\r\n'
 dirname='D64TEST';created_cluster=None
 for step in range(11):
  path=directory/f'workflow-step-{step}.img';fs=Fat12(path.read_bytes());fs.assert_original(original)
  new=set(fs.root)-set(original.root)
  assert new==({dirname} if step<10 else set()),(step,new)
  if step<10:
   e=fs.root[dirname];created_cluster=e['cluster'];entries=fs.directory(e)
   assert entries['.']['cluster']==created_cluster and entries['..']['cluster']==0
   file='T.TXT' if 2<=step<4 else 'R.TXT' if 4<=step<7 else None
   assert set(entries)=={'.','..'}|({file} if file else set()),(step,set(entries))
   if file:
    assert fs.content(entries[file])==expected and entries[file]['size']==len(expected)
   if step>=7:
    raw=fs.cluster(created_cluster);assert raw[64]==0xe5 and raw[65:75]==b'       TXT' or any(raw[i]==0xe5 and raw[i+1:i+11]==b'       TXT' for i in range(64,1024,32)), 'removed file lacks deleted entry'
  authority=original.allocated().copy()
  if step<10:
   authority.update(fs.chain(fs.root[dirname]['cluster']))
   if file:authority.update(fs.chain(entries[file]['cluster']))
  assert fs.allocated()==authority,(step,'orphan or aliased allocation')
  expected_used=2 if 2<=step<7 else 1 if step<10 else 0
  assert len(original.free)-len(fs.free)==expected_used,(step,len(fs.free))
  assert len(fs.allocated())-len(original.allocated())==expected_used
  if step==10:assert fs.value(created_cluster)==0 and any(fs.data[fs.root_lba*512+i]==0xe5 for i in range(0,fs.root_sectors*512,32))
  report.append({'step':step,'sha256':hashlib.sha256(fs.data).hexdigest(),'free_bytes':len(fs.free)*fs.bps*fs.spc,'live_root_entries':len(fs.root)})
 final=Fat12((directory/'workflow-final.img').read_bytes());final.assert_original(original)
 assert set(final.root)==set(original.root) and final.allocated()==original.allocated()
 assert final.data!=source,'test failed to mutate disposable media'
 assert (directory/'workflow-boot.img').read_bytes()==source
 return {'original_sha256':hashlib.sha256(source).hexdigest(),'original_live_root_entries':len(original.root),'all_720_sectors_observed':True,'fat_mirrors_equal_every_checkpoint':True,'original_metadata_and_file_bytes_preserved':True,'deleted_slack_not_required_zero':True,'final_free_bytes':len(final.free)*1024,'checkpoints':report}
if __name__=='__main__':
 import sys
 d=Path(sys.argv[1]);source=Path(sys.argv[2]).read_bytes();print(json.dumps(verify(d,source),indent=2))
