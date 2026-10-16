"""Owned FAT12/FAT16 population. Independent dos_disk_inspect validates output.
Preserves boot sectors, root order and all untouched file cluster allocations.
Input bases with subdirectories are deliberately rejected; new trees are supported.
"""
from dataclasses import dataclass, field
import struct,re
from dos_disk_inspect import Volume

@dataclass
class Item:
    raw: bytearray
    chain: list = field(default_factory=list)
    children: object = None


def short(name):
    if not isinstance(name,str) or name!=name.upper() or not re.fullmatch(r"[A-Z0-9!#$%&'()@^_`{}~-]{1,8}(?:\.[A-Z0-9!#$%&'()@^_`{}~-]{1,3})?",name):
        raise ValueError('strict uppercase DOS 8.3 name: '+str(name))
    parts=name.split('.')
    return (parts[0].ljust(8)+(parts[1] if len(parts)>1 else '').ljust(3)).encode('ascii')

class Populate:
    def __init__(self,data):
        self.original=bytes(data);self.v=Volume(data)
        if self.v.directories: raise ValueError('base directories unsupported; use clean genuine DOS formatted base')
        self.data=bytearray(data);self.tree={};self.expected=dict(self.v.payloads)
        self.width=self.v.width;self.cb=self.v.spc*512
        self.root_slots=self.v.bpb['root_entries']
        self.free=[c for c in range(2,self.v.clusters+2) if self.v.entry(c)==0]
        self.edits=[]
        byname={f['name']:f for f in self.v.files}
        start=self.v.root_sector*512
        for off in range(start,start+self.root_slots*32,32):
            raw=bytearray(data[off:off+32])
            if not raw[0]:break
            if raw[0]==0xe5:continue
            name=raw[:8].decode('cp437').rstrip()+('.'+raw[8:11].decode('cp437').rstrip() if raw[8:11].strip() else '')
            self.tree[name]=Item(raw,byname.get(name,{}).get('clusters',[]))
    def setfat(self,c,value):
        for mirror in range(2):
            base=(self.v.bpb['reserved_sectors']+mirror*self.v.bpb['sectors_per_fat'])*512
            if self.width==16:struct.pack_into('<H',self.data,base+c*2,value)
            else:
                at=base+c*3//2;old=struct.unpack_from('<H',self.data,at)[0]
                word=(old&0xf)|(value<<4) if c&1 else (old&0xf000)|value
                struct.pack_into('<H',self.data,at,word)
    def alloc(self,size):
        count=(size+self.cb-1)//self.cb
        if len(self.free)<count:raise ValueError('disk full')
        chain=self.free[:count];del self.free[:count]
        for i,c in enumerate(chain):self.setfat(c,chain[i+1] if i+1<count else (0xfff if self.width==12 else 0xffff))
        return chain
    def release(self,chain):
        for c in chain:self.setfat(c,0);self.free.append(c)
        self.free.sort()
    def write_chain(self,chain,payload):
        padded=payload+bytes(len(chain)*self.cb-len(payload))
        for i,c in enumerate(chain):
            at=(self.v.data_sector+(c-2)*self.v.spc)*512
            self.data[at:at+self.cb]=padded[i*self.cb:(i+1)*self.cb]
    def node(self,parts):
        parent=self.tree
        for name in parts:
            short(name)
            if name not in parent:
                raw=bytearray(32);raw[:11]=short(name);raw[11]=0x10
                parent[name]=Item(raw,children={})
            item=parent[name]
            if item.children is None:raise ValueError('file blocks directory')
            parent=item.children
        return parent
    def remove(self,path):
        parts=path.split('/');parent=self.node(parts[:-1]);item=parent.pop(parts[-1])
        if item.children is not None:raise ValueError('remove file only')
        self.release(item.chain);self.expected.pop(path);self.edits.append({'remove':path})
    def put(self,path,payload,attr=0x20,replace=False,template=None):
        parts=path.split('/');parent=self.node(parts[:-1]);name=parts[-1];short(name)
        if attr&0xd8:raise ValueError('file attributes')
        if name in parent:
            if not replace or parent[name].children is not None:raise ValueError('explicit replacement required: '+path)
            self.release(parent[name].chain)
        raw=bytearray(template or bytes(32));raw[:11]=short(name);raw[11]=attr
        # Clear reserved/EA fields, retain original creation/write timestamps when supplied.
        raw[12:22]=bytes(10);raw[26:32]=bytes(6)
        chain=self.alloc(len(payload));struct.pack_into('<H',raw,26,chain[0] if chain else 0);struct.pack_into('<I',raw,28,len(payload))
        parent[name]=Item(raw,chain);self.write_chain(chain,payload);self.expected[path]=bytes(payload)
        self.edits.append({'put':path,'bytes':len(payload),'clusters':len(chain),'replace':replace})
    def finish(self):
        if len(self.tree)>self.root_slots:raise ValueError('root directory full')
        def allocate(items):
            for item in items.values():
                if item.children is not None:
                    item.chain=self.alloc((len(item.children)+3)*32)
                    struct.pack_into('<H',item.raw,26,item.chain[0]);allocate(item.children)
        allocate(self.tree)
        def emit(items,parentcluster):
            for item in items.values():
                if item.children is None:continue
                dot=bytearray(32);dot[:11]=b'.          ';dot[11]=0x10;struct.pack_into('<H',dot,26,item.chain[0])
                dots=bytearray(dot);dots[:11]=b'..         ';struct.pack_into('<H',dots,26,parentcluster)
                payload=dot+dots+b''.join(x.raw for x in item.children.values())+bytes(32)
                self.write_chain(item.chain,payload);emit(item.children,item.chain[0])
        emit(self.tree,0)
        at=self.v.root_sector*512
        self.data[at:at+self.root_slots*32]=b''.join(x.raw for x in self.tree.values()).ljust(self.root_slots*32,b'\0')
        result=bytes(self.data);oracle=Volume(result)
        if oracle.payloads!=self.expected:raise AssertionError('independent complete payload mismatch')
        if result[:512]!=self.original[:512]:raise AssertionError('boot sector changed')
        return result,oracle.report()
