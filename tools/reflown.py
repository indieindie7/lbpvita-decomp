# reflown.py <eboot.elf> <funcinfo.tsv> <reflfields.tsv> <out.tsv> : owner class of every reflect function without one.
# Walks callers (bl sites + movw/movt pointer pairs; the 8-byte thunks 0x81607834..0x81607b68 are their own nodes)
# up to 6 levels and stops at the first functions named Reflect_<Class> / ReflectText_<Class> / P<Part>_...
import sys, struct, bisect, re, io, collections
d = open(sys.argv[1], "rb").read(); off, va, fs = 0x80, 0x81000000, 0x85fb54
F = []
for l in io.open(sys.argv[2], encoding="utf-8", errors="replace"):
    p = l.split()
    if p and p[0] == "F": F.append((int(p[1], 16), p[2]))
def u16(a): return struct.unpack_from("<H", d, off + a - va)[0]
for a in range(0x81607834, 0x81607b68, 2):
    if u16(a) == 0xb510 and u16(a + 6) == 0xbd10: F.append((a, "thunk_%08x" % a))
F.sort(); K = [a for a, _ in F]; S = set(K); NM = dict(F)
def owner(a): return K[bisect.bisect_right(K, a) - 1]
callers = collections.defaultdict(set)
def imm16(h1, h2): return ((h1 & 0xf) << 12) | (((h1 >> 10) & 1) << 11) | (((h2 >> 12) & 7) << 8) | (h2 & 0xff)
for o in range(0, fs - 4, 2):
    h1, h2 = struct.unpack_from("<HH", d, off + o)
    if (h1 & 0xf800) == 0xf000 and (h2 & 0xd000) == 0xd000:
        s = (h1 >> 10) & 1; j1 = (h2 >> 13) & 1; j2 = (h2 >> 11) & 1
        imm = (s << 24) | ((1 - (j1 ^ s)) << 23) | ((1 - (j2 ^ s)) << 22) | ((h1 & 0x3ff) << 12) | ((h2 & 0x7ff) << 1)
        if s: imm -= 1 << 25
        t = va + o + 4 + imm
        if t in S: callers[t].add(owner(va + o))
    elif (h1 & 0xfbf0) == 0xf240 and not (h2 & 0x8000):
        rd = (h2 >> 8) & 0xf; lo = imm16(h1, h2)
        for k in range(4, 28, 2):
            g1, g2 = struct.unpack_from("<HH", d, off + o + k)
            if (g1 & 0xfbf0) == 0xf2c0 and not (g2 & 0x8000) and ((g2 >> 8) & 0xf) == rd:
                t = ((imm16(g1, g2) << 16) | lo) & ~1
                if t in S and 0x81000000 <= t < 0x81860000: callers[t].add(owner(va + o))
                break
def cls(n):
    m = re.match(r"(?:ReflectText|Reflect)_(\w+)$", n)
    if m and m.group(1) != "NoFields": return m.group(1)
    m = re.match(r"(P[A-Z][A-Za-z]+)_", n)
    return m.group(1) if m else None
rows = collections.OrderedDict()
for l in io.open(sys.argv[3], encoding="utf-8").read().split("\n")[1:]:
    f = l.split("\t")
    if len(f) > 3: rows.setdefault(f[0], [f[1], []])[1].append(f[3])
out = ["func\tname\tdepth\towners\tfields"]; st = collections.Counter()
for a, (n, fl) in rows.items():
    x = int(a, 16)
    if cls(NM.get(x, n)): continue
    seen = {x}; front = {x}; own = set(); depth = 0
    while front and not own and depth < 6:
        depth += 1; nxt = set()
        for f in front:
            for c in callers.get(f, ()):
                if c in seen: continue
                seen.add(c); k = cls(NM[c])
                if k: own.add("%s:%08x" % (k, c))
                else: nxt.add(c)
        front = nxt
    ks = sorted({o.split(":")[0] for o in own})
    st["none" if not ks else "one" if len(ks) == 1 else "shared"] += 1
    out.append("%s\t%s\t%d\t%s\t%s" % (a, NM.get(x, n), depth, ",".join(sorted(own)[:6]), " ".join(fl[:4])))
io.open(sys.argv[4], "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print(len(out) - 1, dict(st))
