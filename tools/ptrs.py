# ptrs.py <elf> <va hex> : where is this va stored as a 32-bit pointer; dump 8 words around each site
import sys,struct
d=open(sys.argv[1],'rb').read(); va=int(sys.argv[2],16)
def o2va(o): return 0x81000000+o-0x80 if o<0x860080 else 0x81860000+o-0x860080
k=struct.pack('<I',va); i=0
while True:
    i=d.find(k,i)
    if i<0: break
    w=struct.unpack_from('<12I',d,i-16)
    print('%08x: '%o2va(i-16)+' '.join('%08x'%x for x in w)); i+=4
