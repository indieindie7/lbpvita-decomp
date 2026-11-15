import struct,re,sys
R="C:/Users/john/Documents/LBPVita/"
S=sys.argv[1]
d=open(R+'bin/eboot.elf','rb').read()
phoff=struct.unpack_from('<I',d,0x1c)[0]; phes,phn=struct.unpack_from('<HH',d,0x2a)
def off(v):
    for i in range(phn):
        t,o,va,pa,fs,ms=struct.unpack_from('<IIIIII',d,phoff+i*phes)
        if t==1 and va<=v<va+fs: return o+v-va
T={}
for l in open(R+'ghidra/work/lamskeys.tsv',encoding='utf-8'):
    h,k=l.rstrip('\n').split('\t'); T[int(h,16)]=k
base=0x81496aaa
tg={}
for i in range(0x6e):
    h=struct.unpack_from('<H',d,off(base+i*2))[0]
    tg.setdefault(base+h*2,[]).append(i+1)
ins=[]
for f in ('fc3.asm','fc3b.asm'):
    for l in open(S+'/'+f):
        m=re.match(r'([0-9a-f]{8}) (\S+)\s+(.*)',l)
        if m: ins.append((int(m.group(1),16),m.group(2),m.group(3)))
ts=sorted(tg)
rows=[]
for n,t in enumerate(ts):
    e=ts[n+1] if n+1<len(ts) else 0x8149a3ae
    lo={};hi={};out=[];calls=set()
    for a,op,arg in ins:
        if not(t<=a<e): continue
        m=re.match(r'(r\d+), #(0x[0-9a-f]+|\d+)',arg)
        if op=='movw' and m: lo[m.group(1)]=int(m.group(2),0)
        elif op=='movt' and m:
            r=m.group(1)
            if r in lo:
                v=(int(m.group(2),0)<<16)|lo[r]
                if v in T: out.append(T[v])
                elif r=='r2': out.append('?%08x'%v)
        elif op=='bl': calls.add(arg.strip('#'))
        elif op.startswith('b') and op not in('bl','blx','bx') and '0x8149a22c' in arg and op in('b','b.w'): break
    rows.append((tg[t],t,out,calls))
for ty,t,out,calls in sorted(rows,key=lambda r:r[0][0]):
    print('%s\t%x\t%s\t%s'%(','.join('0x%02x'%x for x in ty),t,' '.join(out),' '.join(sorted(calls-{'0x81495d68'}))))
