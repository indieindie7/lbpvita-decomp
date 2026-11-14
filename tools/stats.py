import sys,re,collections
F=[];cur=None
for l in open(sys.argv[1],encoding='utf8',errors='replace'):
    t=l.rstrip('\n').split(' ',1)
    if t[0]=='F':
        a,n,src,sz=t[1].split(' '); cur={'a':int(a,16),'n':n,'src':src,'sz':int(sz),'C':[],'S':[]}; F.append(cur)
    elif t[0]=='C': cur['C'].append(int(t[1],16))
    elif t[0]=='S': cur['S'].append(t[1])
code=[f for f in F if 0x81000000<=f['a']<0x81763e38]
print('funcs',len(F),'in code',len(code),'bytes',sum(f['sz'] for f in code),'of',0x763e38)
ws=sum(1 for f in F if f['S']); print('with strings',ws)
src=collections.Counter()
for f in F:
    for s in f['S']:
        m=re.search(r'([\w]+)\.(cpp|h|c|inl)$',s)
        if m and '/' in s: src[s]+=1
print('src path strings referenced',len(src),sum(src.values())); print(src.most_common(8))
sc=collections.Counter(s for f in F for s in set(f['S']))
print('unique-owner strings',sum(1 for s,c in sc.items() if c==1))
print('funcs with a unique string',sum(1 for f in F if any(sc[s]==1 for s in f['S'])))
imp={f['a'] for f in F if f['src']=='IMPORTED'}
print('funcs calling imports directly',sum(1 for f in F if any(c in imp for c in f['C'])))
gaps=[];code.sort(key=lambda f:f['a'])
