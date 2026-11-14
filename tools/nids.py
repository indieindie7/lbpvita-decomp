import re,sys,glob
db={}
for f in glob.glob(sys.argv[1]+'/db/**/*.yml',recursive=True):
    lib=None;sec=None
    for l in open(f,encoding='utf8'):
        m=re.match(r'^\s+(\w+):\s*(0x[0-9A-Fa-f]+)\s*$',l)
        if m: db.setdefault(int(m.group(2),16),m.group(1))
hit=0;tot=0
out=open(sys.argv[3],'w')
for l in open(sys.argv[2]):
    lib,lnid,k,nid,addr=l.split()
    tot+=1; n=db.get(int(nid,16))
    if n: hit+=1
    else: n='%s_%s'%(lib,nid.upper())
    out.write('0x%s %s %s imp %s\n'%(addr,'func' if k=='F' else 'data',n,lib))
print('resolved',hit,'of',tot)
