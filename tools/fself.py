import struct,sys,zlib
p=sys.argv[1]; d=open(p,'rb').read()
magic,ver,sdk,hdrtype,metaoff,hdrlen,elflen,selflen=struct.unpack_from('<4sIHHIQQQ',d,0)
print('magic',magic,'ver',ver,'type',hdrtype,'metaoff',hex(metaoff),'hdrlen',hex(hdrlen),'elflen',hex(elflen),'selflen',hex(selflen))
# SCE ext header at 0x20
appinfo,elfoff,phoff,shoff,seginfo,sceveroff,ctrloff,ctrlsize,_x=struct.unpack_from('<9Q',d,0x38)
print('appinfo',hex(appinfo),'elfoff',hex(elfoff),'phoff',hex(phoff),'seginfo',hex(seginfo),'ctrl',hex(ctrloff),hex(ctrlsize))
e=d[elfoff:elfoff+0x34]
print('elf',e[:16].hex())
etype,mach,ever,entry,ephoff,eshoff,flags,ehsz,phsz,phnum,shsz,shnum,shstr=struct.unpack_from('<HHIIIIIHHHHHH',e,16)
print('etype',hex(etype),'mach',mach,'entry',hex(entry),'phnum',phnum,'shnum',shnum)
for i in range(phnum):
    pt,off,va,pa,fsz,msz,fl,al=struct.unpack_from('<8I',d,phoff+i*32)
    so,sl,comp,enc=struct.unpack_from('<QQQQ',d,seginfo+i*32)
    print(i,'pt',hex(pt),'off',hex(off),'va',hex(va),'fsz',hex(fsz),'msz',hex(msz),'fl',fl,'| seg off',hex(so),'len',hex(sl),'comp',comp,'enc',enc)
