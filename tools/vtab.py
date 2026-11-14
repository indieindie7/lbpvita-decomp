# vtab.py <elf> <funcinfo.tsv> <vtable va hex> [n] : list vtable slots (thumb code pointers) with function name and size
import sys,struct
d=open(sys.argv[1],'rb').read(); F={}
for l in open(sys.argv[2],encoding='utf8',errors='replace'):
    if l.startswith('F '):
        t=l.split(); F[int(t[1],16)]=(t[2],t[4])
va=int(sys.argv[3],16); n=int(sys.argv[4]) if len(sys.argv)>4 else 64
o=va-0x81000000+0x80
for i in range(n):
    p=struct.unpack_from('<I',d,o+4*i)[0]
    if not (p&1 and 0x81000000<=p<0x81763e38): break
    nm=F.get(p-1,('?','?')); print('%2d +%03x %08x %s %s'%(i,4*i,p-1,nm[0],nm[1]))
