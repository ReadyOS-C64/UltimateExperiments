import zlib
def resign(x):x=bytearray(x);x[572:]=zlib.crc32(x[:572]).to_bytes(4,'little');return bytes(x)
def cfg():
 b=bytearray(576);b[:7]=b'D64C\1\x40\2'
 for a,s in [(8,b'/usb1/Owned'),(136,b'/usb1/Media/A.IMG'),(264,b'/sd/Media/B.IMG'),(392,b'/usb1/HD/C.IMG')]:b[a:a+len(s)]=s
 b[524]=6;b[525]=7;b[528:536]=bytes.fromhex('78563412cdab3412');b[536]=1;b[540]=64
 return resign(b)
