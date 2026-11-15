# natives2.py <elf> <hand.txt> <out> : script natives that natives.py missed (signatures with '.' or longer than 120),
# only addresses not yet in hand.txt; overloads get the address as suffix.
import sys,struct,re,collections
d=open(sys.argv[1],'rb').read()
def va2o(v):
    if 0x81000000<=v<0x8185fb54: return v-0x81000000+0x80
    if 0x81860000<=v<0x81bc7290: return v-0x81860000+0x860080
def cstr(v):
    o=va2o(v)
    if o is None: return None
    s=d[o:d.find(b'\0',o)]
    return s.decode() if 3<len(s)<400 and re.fullmatch(rb'\w+__[\w.]*',s) else None
have={}
for l in open(sys.argv[2],encoding='utf-8'):
    p=l.split()
    if len(p)>2: have[int(p[0],16)]=p[2]
used=collections.Counter(have.values())
seen={}
for o in range(0x80,len(d)-12,4):
    f,p,fl=struct.unpack_from('<III',d,o)
    if f&1 and 0x81000000<=f<0x81763e38 and fl<4:
        s=cstr(p)
        if s: seen.setdefault(f-1,(s,fl))
cnt=collections.Counter(s.split('__')[0] for s,_ in seen.values())
out=open(sys.argv[3],'w',newline='\n');n=0
for a in sorted(seen):
    if a in have: continue
    s,fl=seen[a]; nm='native_'+s.split('__')[0]
    if cnt[s.split('__')[0]]>1 or used[nm]: nm+='_%08x'%a
    out.write('0x%08x func %s hand late67 script native %s flag=%d\n'%(a,nm,s,fl)); n+=1
print('new',n,'total',len(seen))
