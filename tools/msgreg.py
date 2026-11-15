# msgreg.py <eboot.elf> <funcinfo.tsv> [enums.txt] : every call of Net_RegisterHandler 0x812c0a14
# -> type, handler stub (movw/movt r2), registering function. Output TSV.
import sys, struct, bisect, re
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
names = {}
if len(sys.argv) > 3:
    for l in open(sys.argv[3], encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)\s+(E_MESSAGE\w+)", l)
        if m: names.setdefault(int(m.group(1)), m.group(2).replace("E_MESSAGE_TYPE_", ""))
TGT = 0x812c0a14
def imm16(h1, h2): return ((h1 & 0xf) << 12) | (((h1 >> 10) & 1) << 11) | (((h2 >> 12) & 7) << 8) | (h2 & 0xff)
rows = []
for o in range(0, fs - 4, 2):
    h1, h2 = struct.unpack_from("<HH", d, off + o)
    if (h1 & 0xf800) != 0xf000 or (h2 & 0xd000) != 0xd000: continue
    s = (h1 >> 10) & 1; j1 = (h2 >> 13) & 1; j2 = (h2 >> 11) & 1
    imm = (s << 24) | ((1 - (j1 ^ s)) << 23) | ((1 - (j2 ^ s)) << 22) | ((h1 & 0x3ff) << 12) | ((h2 & 0x7ff) << 1)
    if s: imm -= 1 << 25
    if (va + o + 4 + imm) & 0xffffffff != TGT: continue
    typ = lo = hi = None
    p = o - 2
    while p > o - 0x30 and (typ is None or lo is None or hi is None):
        a, b = struct.unpack_from("<HH", d, off + p)
        if typ is None and (a & 0xff00) == 0x2100: typ = a & 0xff          # movs r1,#imm8
        if (b & 0x8f00) == 0x0200:
            if lo is None and (a & 0xfbf0) == 0xf240: lo = imm16(a, b)
            if hi is None and (a & 0xfbf0) == 0xf2c0: hi = imm16(a, b)
        p -= 2
    i = bisect.bisect_right(K, va + o) - 1
    h = ((hi or 0) << 16 | (lo or 0)) & ~1
    j = bisect.bisect_right(K, h) - 1
    rows.append((typ if typ is not None else -1, h, F[j][1] if K[j] == h else "?", va + o, F[i][0], F[i][1]))
for r in sorted(rows):
    print("0x%02x\t%s\t%08x\t%s\t%08x\t%08x\t%s" % (r[0], names.get(r[0], ""), r[1], r[2], r[3], r[4], r[5]))
