# autoname.py <funcinfo.tsv> <out names.txt>: provisional names for every FUN_ from funcinfo only (no decompile).
# Tags: str = named from a referenced string, src = only a source-path string, imp = from the SDK imports it calls,
# rule = structural (size / callee count) with the nearest source-file anchor as area. All provisional.
import sys,re,collections,bisect
F=[];cur=None
for l in open(sys.argv[1],encoding='utf8',errors='replace'):
    t=l.rstrip('\n').split(' ',1)
    if t[0]=='F':
        a,n,src,sz=t[1].split(' '); cur={'a':int(a,16),'n':n,'sz':int(sz),'C':[],'S':[]}; F.append(cur)
    elif t[0]=='C': cur['C'].append(int(t[1],16))
    elif t[0]=='S': cur['S'].append(t[1])
by={f['a']:f for f in F}
PATH=re.compile("[/"+chr(92)*2+"]([A-Za-z0-9_]+)[.](cpp|h|c|inl)$")
def stem(s):
    m=PATH.search(s)
    return m.group(1) if m and len(s)<200 else None
sc=collections.Counter(s for f in F for s in set(f['S']))
callcnt=collections.Counter(c for f in F for c in set(f['C']))
def slug(s):
    w=re.findall(r'[A-Za-z][A-Za-z0-9]+',s)
    out=''
    for x in w:
        if len(out)+len(x)>34: break
        out+=x[0].upper()+x[1:]
    return out
def wordy(s):
    return len(re.findall(r'[A-Za-z]{3,}',s))>=1 and '%' not in s[:1]
anchors=[]  # (addr, stem) from functions that reference a .cpp path
for f in F:
    st=[stem(s) for s in f['S']]; cpp=[x for x,s in zip(st,f['S']) if x and s.endswith('.cpp')]
    f['stem']=(cpp or [x for x in st if x] or [None])[0]
    if cpp: anchors.append((f['a'],cpp[0]))
anchors.sort(); ak=[a for a,_ in anchors]
def area(a):
    i=bisect.bisect_left(ak,a)
    p=anchors[i-1] if i>0 else None; n=anchors[i] if i<len(ak) else None
    if p and n and n[0]-p[0]<=0x4000:
        if p[1]==n[1]: return p[1]
        if p[1].split('_')[0]==n[1].split('_')[0] and '_' in p[1]: return p[1].split('_')[0]
    best=None
    for x in (p,n):
        if x and abs(x[0]-a)<=0x300 and (best is None or abs(x[0]-a)<best[0]): best=(abs(x[0]-a),x[1])
    return best[1] if best else 'lbp'
out=[];cnt=collections.Counter();used=set()
def emit(f,name,tag,note):
    name=re.sub(r'\W','_',name)+'_%08x'%f['a']
    f['new']=name; cnt[tag]+=1
    out.append('0x%08x func %s %s %s'%(f['a'],name,tag,note))
todo=[f for f in F if f['n'].startswith('FUN_')]
for f in todo:
    a=f['a'];C=f['C'];S=f['S']
    imps=[by[c]['n'] for c in C if c in by and not by[c]['n'].startswith(('FUN_','thunk_'))]
    desc=[s for s in S if not stem(s) and wordy(s) and len(slug(s))>=4]
    if desc:
        uniq=[s for s in desc if sc[s]==1]
        s=max(uniq or desc,key=lambda x:(min(len(slug(x)),34),-sc[x]))
        emit(f,'%s_%s'%(f['stem'] or area(a),slug(s)),'str','provisional string%s'%('' if uniq else ' shared'))
    elif f['stem']:
        emit(f,'%s_fn'%f['stem'],'src','provisional source-path string')
    elif imps:
        i=min(set(imps),key=lambda n:callcnt[[k for k in C if by[k]['n']==n][0]])
        emit(f,'%s_use_%s'%(area(a),i),'imp','provisional calls %d imports'%len(set(imps)))
    else:
        n=f['sz'];c=len(set(C))
        role='Stub' if n<=4 else 'Leaf%s'%('S' if n<=16 else 'M' if n<=96 else 'L') if c==0 else ('Thunk' if n<=12 else 'Wrap') if c==1 else 'Proc' if c<10 else 'Run'
        emit(f,'%s_%s'%(area(a),role),'rule','provisional size=%d callees=%d'%(n,c))
open(sys.argv[2],'w',encoding='utf8').write('\n'.join(out)+'\n')
print(len(todo),dict(cnt)); print('areas',collections.Counter(l.split()[2].split('_')[0] for l in out).most_common(6))
