# natives.py <elf> <out> : script-native table entries {thumb func ptr, name ptr "Name__Sig", flag} (12 bytes) -> hand-format names
import sys,struct,re,collections
d=open(sys.argv[1],'rb').read()
def va2o(v):
    if 0x81000000<=v<0x8185fb54: return v-0x81000000+0x80
    if 0x81860000<=v<0x81bc7290: return v-0x81860000+0x860080
def cstr(v):
    o=va2o(v)
    if o is None: return None
    e=d.find(b'\0',o)
    s=d[o:e]
    return s.decode() if 3<len(s)<120 and re.fullmatch(rb'[\w]+__[\w]*',s) else None
seen={};n=0;names=collections.Counter()
for o in range(0x80,len(d)-12,4):
    f,p,fl=struct.unpack_from('<III',d,o)
    if f&1 and 0x81000000<=f<0x81763e38 and fl<4:
        s=cstr(p)
        if s:
            n+=1; seen.setdefault(f-1,[]).append((s,fl))
out=open(sys.argv[2],'w')
for a in sorted(seen):
    s,fl=seen[a][0]; nm,sig=s.split('__',1)
    names[nm]+=1
    out.write('0x%08x func native_%s%s hand script native %s flag=%d%s\n'%(a,nm,'' if len(seen[a])==1 else '', s,fl,'' if len(seen[a])==1 else ' (+%d aliases: %s)'%(len(seen[a])-1,','.join(x[0] for x in seen[a][1:4]))))
print('entries',n,'functions',len(seen),'dup names',sum(1 for k,v in names.items() if v>1))
