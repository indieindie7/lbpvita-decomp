import struct,sys
d=open(sys.argv[1],'rb').read()
hdrlen,elflen=struct.unpack_from('<QQ',d,0x10)
elfoff,phoff=struct.unpack_from('<QQ',d,0x40)
out=bytearray(elflen)
out[:0x34]=d[elfoff:elfoff+0x34]
phnum=struct.unpack_from('<H',out,0x2c)[0]; eph=struct.unpack_from('<I',out,0x1c)[0]
out[eph:eph+phnum*32]=d[phoff:phoff+phnum*32]
for i in range(phnum):
    pt,off,va,pa,fsz,msz,fl,al=struct.unpack_from('<8I',d,phoff+i*32)
    out[off:off+fsz]=d[hdrlen+off:hdrlen+off+fsz]
open(sys.argv[2],'wb').write(out)
