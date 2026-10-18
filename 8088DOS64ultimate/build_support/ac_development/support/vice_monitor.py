"""Small framed VICE binary-monitor client; no launch or hardware behavior."""
import struct
class BinaryMonitor:
    def __init__(self,sock):self.sock=sock;self.ident=0
    def _exact(self,n):
        parts=bytearray()
        while len(parts)<n:
            chunk=self.sock.recv(n-len(parts))
            if not chunk:raise EOFError('VICE monitor closed mid-packet')
            parts.extend(chunk)
        return bytes(parts)
    def call(self,typ,body=b''):
        self.ident+=1
        self.sock.sendall(struct.pack('<BBIIB',2,2,len(body),self.ident,typ)+body)
        for _ in range(128):
            stx,api,length,reply,error,ident=struct.unpack('<BBIBBI',self._exact(12))
            if stx!=2 or api!=2 or length>1024*1024:raise ValueError('Invalid VICE response frame')
            data=self._exact(length)
            if ident==0xffffffff:continue
            if ident!=self.ident or reply!=typ:raise ValueError('Mismatched VICE response')
            if error:raise ValueError(f'VICE command {typ:02x} failed with {error:02x}')
            return data
        raise ValueError('Too many VICE events without command response')
    def banks(self):
        data=self.call(0x82)
        if len(data)<2:raise ValueError('Missing bank count')
        count=int.from_bytes(data[:2],'little');pos=2;result={}
        for _ in range(count):
            if pos>=len(data):raise ValueError('Missing bank record')
            size=data[pos]
            if size<3 or pos+1+size>len(data):raise ValueError('Invalid bank record')
            bank=int.from_bytes(data[pos+1:pos+3],'little');length=data[pos+3]
            if length+3!=size:raise ValueError('Invalid bank name length')
            name=data[pos+4:pos+4+length].decode('ascii')
            if name in result:raise ValueError('Duplicate bank name')
            result[name]=bank;pos+=size+1
        if pos!=len(data):raise ValueError('Trailing bank data')
        return result
    def read(self,start,end,bank):
        if not 0<=start<=end<=65535 or not 0<=bank<=65535:raise ValueError('Invalid memory range')
        data=self.call(1,struct.pack('<BHHBH',0,start,end,0,bank));length=end-start+1
        if len(data)!=length+2 or int.from_bytes(data[:2],'little')!=(length&65535):raise ValueError('Short VICE memory reply')
        return data[2:]
    def resource(self,name):
        raw=name.encode('ascii')
        if not 0<len(raw)<256:raise ValueError('Invalid resource name')
        data=self.call(0x51,bytes([len(raw)])+raw)
        if len(data)<2 or len(data)!=data[1]+2:raise ValueError('Bad resource framing')
        if data[0]==1:
            if data[1]!=4:raise ValueError('Bad integer resource length')
            return int.from_bytes(data[2:],'little')
        if data[0]==0:return data[2:].decode('utf-8')
        raise ValueError('Unknown resource type')
