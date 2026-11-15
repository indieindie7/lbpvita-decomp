# classes.py <vtables.tsv> <funcinfo.tsv> <classes.tsv> <CLASSES.md> [classnames.txt] : class tree from vtables.
# base of V = a vtable P with slots(P) <= slots(V), sharing slot functions at the same index, whose
# ctor/dtor is called by (or inlined in) a ctor/dtor of V. Names come from hand names *_ctor / *_dtor, else cls_<va>.
import sys, re, collections
vt = {}
for l in open(sys.argv[1], encoding='utf8'):
    va, n, r, refs, slots = l.rstrip('\n').split('\t')
    vt[int(va, 16)] = (slots.split(' '), [x for x in refs.split(',') if x != '-'])
name2addr = {}; callees = collections.defaultdict(set); cur = None; kind = {}
for l in open(sys.argv[2], encoding='utf8', errors='replace'):
    t = l.split()
    if len(t) >= 3 and t[0] == 'F': cur = t[2]; name2addr[cur] = int(t[1], 16); kind[cur] = t[3]
    elif len(t) == 2 and t[0] == 'C' and cur: callees[cur].add(int(t[1], 16))
addr2name = {a: n for n, a in name2addr.items()}
reff = collections.defaultdict(set)
for v, (s, refs) in vt.items():
    for f in refs: reff[f].add(v)
def share(a, b):
    return sum(1 for x, y in zip(vt[a][0], vt[b][0]) if x == y and 'Stub_81000000' not in x)
def reach(a, b):
    # fraction of the functions referencing vtable a that also reference b or call a function referencing b
    fs = vt[a][1]
    if not fs: return 0.0
    k = 0
    for f in fs:
        if b in reff[f] or any(b in reff.get(addr2name.get(c, ''), ()) for c in callees[f]): k += 1
    return k / len(fs)
base = {}
for v, (s, refs) in vt.items():
    cand = set()
    for f in refs:
        cand |= reff[f]
        for c in callees[f]:
            cand |= reff.get(addr2name.get(c, ''), set())
    best = None
    for p in cand:
        if p == v or len(vt[p][0]) > len(s): continue
        sh = share(v, p)
        if sh < 2 and sh < len(vt[p][0]): continue
        if reach(v, p) <= reach(p, v): continue
        key = (len(vt[p][0]), sh, -p)
        if best is None or key > best[0]: best = (key, p)
    if best: base[v] = best[1]
# break cycles
for v in list(base):
    seen = {v}; p = base[v]
    while p in base:
        if p in seen: del base[v]; break
        seen.add(p); p = base[p]
extra = {}
if len(sys.argv) > 5:
    for l in open(sys.argv[5], encoding='utf8'):
        t = l.split()
        if len(t) >= 2 and not l.startswith('#'): extra[int(t[0], 16)] = t[1]
def cname(v):
    if v in extra: return extra[v]
    for f in vt[v][1]:
        m = re.match(r'(.+)_(ctor|dtor)$', f)
        if m and len(reff[f]) == 1: return m.group(1)
    return 'cls_%08x' % v
kids = collections.defaultdict(list)
for v, p in base.items(): kids[p].append(v)
with open(sys.argv[3], 'w', encoding='utf8', newline='\n') as f:
    for v in sorted(vt):
        s, refs = vt[v]
        own = [i for i, x in enumerate(s) if v not in base or i >= len(vt[base[v]][0]) or vt[base[v]][0][i] != x]
        f.write('%08x\t%s\t%d\t%s\t%s\t%s\n' % (v, cname(v), len(s), '%08x' % base[v] if v in base else '-', ','.join(refs) or '-', ','.join(map(str, own))))
roots = [v for v in sorted(vt) if v not in base]
def size(v): return 1 + sum(size(k) for k in kids[v])
with open(sys.argv[4], 'w', encoding='utf8', newline='\n') as f:
    f.write('# LBP Vita class trees (from vtables, no RTTI in the binary)\n\n')
    f.write('Made by tools/vtscan.py + tools/classes.py. %d vtables, %d with a base found, %d roots. Names: hand names of the constructor, then ghidra/classnames.txt (from strings in the own virtual functions of the class, not constructor-verified), else cls_<vtable address>. Each line: name, vtable, slot count, own or overridden slots.\n\n' % (len(vt), len(base), len(roots)))
    def emit(v, d):
        s = vt[v][0]
        own = sum(1 for i, x in enumerate(s) if v not in base or i >= len(vt[base[v]][0]) or vt[base[v]][0][i] != x)
        f.write('%s- %s 0x%08x slots %d own %d\n' % ('  ' * d, cname(v), v, len(s), own))
        for k in sorted(kids[v]): emit(k, d + 1)
    for v in sorted(roots, key=lambda x: -size(x)):
        if size(v) > 1: emit(v, 0)
    f.write('\n## Classes with no base and no children found\n')
    f.write(' '.join('0x%08x(%d)' % (v, len(vt[v][0])) for v in roots if size(v) == 1) + '\n')
print('vtables', len(vt), 'based', len(base), 'roots', len(roots), 'trees>1', sum(1 for v in roots if size(v) > 1), 'biggest', sorted((size(v) for v in roots), reverse=True)[:8])
