import struct,sys
d=open(sys.argv[1],'rb').read()
entry=struct.unpack_from('<I',d,0x18)[0]
phs=[struct.unpack_from('<8I',d,0x34+i*32) for i in range(struct.unpack_from('<H',d,0x2c)[0])]
def o(va):
    for pt,off,v,pa,fsz,msz,fl,al in phs:
        if v<=va<v+fsz: return off+va-v
    return None
seg=entry>>30; mo=phs[seg][1]+(entry&0x3fffffff)
print('modinfo seg',seg,'fileoff',hex(mo))
attr,ver,name,typ,gp,exp_top,exp_end,imp_top,imp_end=struct.unpack_from('<HH27sBIIIII',d,mo)
print(name.rstrip(b'\0'),hex(attr),'exp',hex(exp_top),hex(exp_end),'imp',hex(imp_top),hex(imp_end))
print(d[mo:mo+0x60].hex())
base=phs[seg][2]; so=phs[seg][1]
p=so+exp_top
while p<so+exp_end:
    sz,ver,at,nf,nv,nt,_,lnid,lname,nidt,entt=struct.unpack_from('<HHHHHHIIIII',d,p)
    nm=d[o(lname):].split(b'\0')[0] if lname else b''
    print('EXP',nm,hex(lnid),'nf',nf,'nv',nv)
    for i in range(nf+nv):
        print('  ',hex(struct.unpack_from('<I',d,o(nidt)+4*i)[0]),hex(struct.unpack_from('<I',d,o(entt)+4*i)[0]))
    p+=sz
p=so+imp_top; out=open(sys.argv[2],'w'); n=0;libs=0
while p<so+imp_end:
    sz=struct.unpack_from('<H',d,p)[0]
    if sz==0x34:
        sz,ver,at,nf,nv,nt,_,lnid,lname,_2,fnid,fent,vnid,vent,tn,te=struct.unpack_from('<HHHHHHIIIIIIIIII',d,p)
    else:
        sz,ver,at,nf,nv,_u,lnid,lname,fnid,fent,vnid,vent=struct.unpack_from('<HHHHHHIIIIII',d,p)
    nm=d[o(lname):].split(b'\0')[0].decode(); libs+=1
    for i in range(nf):
        out.write('%s\t%08x\tF\t%08x\t%08x\n'%(nm,lnid,struct.unpack_from('<I',d,o(fnid)+4*i)[0],struct.unpack_from('<I',d,o(fent)+4*i)[0])); n+=1
    for i in range(nv):
        out.write('%s\t%08x\tV\t%08x\t%08x\n'%(nm,lnid,struct.unpack_from('<I',d,o(vnid)+4*i)[0],struct.unpack_from('<I',d,o(vent)+4*i)[0]))
    p+=sz
print('import libs',libs,'funcs',n)
