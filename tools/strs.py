# strs.py <elf> <regex> : strings (va, text) matching regex, case-insensitive
import re,sys
d=open(sys.argv[1],'rb').read(); rx=re.compile(sys.argv[2],re.I)
for m in re.finditer(rb'[\x20-\x7e]{4,}',d):
    s=m.group().decode()
    if rx.search(s):
        o=m.start(); va=0x81000000+o-0x80 if o<0x860080 else 0x81860000+o-0x860080
        print('%08x %s'%(va,s[:140]))
