# blscan.py <eboot.elf> <funcinfo.tsv> <addr...> : every Thumb-2 BL / B.W whose target is addr,
# with the function that holds it. Finds tail jumps (b.w) that the funcinfo call list misses.
import sys, struct, bisect
d = open(sys.argv[1], "rb").read()
phoff = struct.unpack_from("<I", d, 0x1c)[0]; phes, phnum = struct.unpack_from("<HH", d, 0x2a)
seg = None
for i in range(phnum):
    t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<8I", d, phoff + i * phes)
    if t == 1 and fl & 1 and seg is None: seg = (off, va, fs)
off, va, fs = seg
F = []
for l in open(sys.argv[2], encoding="utf-8", errors="replace"):
    p = l.split()
    if p and p[0] == "F": F.append((int(p[1], 16), p[2]))
F.sort(); K = [a for a, _ in F]
T = {int(a, 16) for a in sys.argv[3:]}
for o in range(0, fs - 4, 2):
    h1, h2 = struct.unpack_from("<HH", d, off + o)
    if (h1 & 0xf800) != 0xf000 or (h2 & 0x8000) == 0: continue
    kind = (h2 >> 12) & 5
    if kind not in (5, 1): continue   # 5 = BL, 1 = B.W
    s = (h1 >> 10) & 1; j1 = (h2 >> 13) & 1; j2 = (h2 >> 11) & 1
    i1 = 1 - (j1 ^ s); i2 = 1 - (j2 ^ s)
    imm = (s << 24) | (i1 << 23) | (i2 << 22) | ((h1 & 0x3ff) << 12) | ((h2 & 0x7ff) << 1)
    if s: imm -= 1 << 25
    tgt = (va + o + 4 + imm) & 0xffffffff
    if tgt in T:
        i = bisect.bisect_right(K, va + o) - 1
        print("%08x %s %08x in %08x %s" % (tgt, "bl" if kind == 5 else "b.w", va + o, F[i][0], F[i][1]))
