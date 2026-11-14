# enums.py <elf> <out.txt> : reflection enum tables = runs of {char* name, int value} (8 bytes) with >= 4 identifier names
import sys,struct,re
d=open(sys.argv[1],'rb').read()
def va2o(v):
    if 0x81000000<=v<0x8185fb54: return v-0x81000000+0x80
    if 0x81860000<=v<0x81bc7290: return v-0x81860000+0x860080
def o2va(o): return 0x81000000+o-0x80 if o<0x860080 else 0x81860000+o-0x860080
ID=re.compile(rb'[A-Za-z_][A-Za-z0-9_]{2,80}')
def name(v):
    o=va2o(v)
    if o is None: return None
    e=d.find(b'\0',o,o+90)
    if e<0: return None
    s=d[o:e]
    return s.decode() if ID.fullmatch(s) else None
out=open(sys.argv[2],'w');o=0x80;nt=0;ne=0
while o<len(d)-8:
    run=[];p=o
    while p<len(d)-8:
        v,s=struct.unpack_from('<II',d,p); n=name(s)
        if not n or (v>0x10000 and v<0xffff0000): break
        run.append((n,v)); p+=8
    if len(run)>=4 and sum(1 for n,_ in run if n.isupper() or '_' in n)>=len(run)*0.7:
        out.write('TABLE %08x n=%d\n'%(o2va(o),len(run)))
        for n,v in run: out.write('  %d %s\n'%(v if v<0x80000000 else v-(1<<32),n))
        nt+=1;ne+=len(run);o=p
    else: o+=4
print('tables',nt,'entries',ne)
