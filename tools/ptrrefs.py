# ptrrefs.py <eboot.elf> <funcinfo.tsv> <targets file: hex addr per line or tsv col 0> : Thumb-2 movw/movt pairs (same register, movt within 24 bytes) whose value is target|1 or target
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
T = set()
for l in open(sys.argv[3], encoding="utf-8"):
    p = l.split("\t")[0].strip()
    try: T.add(int(p, 16))
    except ValueError: pass
def imm16(h1, h2): return ((h1 & 0xf) << 12) | (((h1 >> 10) & 1) << 11) | (((h2 >> 12) & 7) << 8) | (h2 & 0xff)
for o in range(0, fs - 4, 2):
    h1, h2 = struct.unpack_from("<HH", d, off + o)
    if (h1 & 0xfbf0) != 0xf240 or (h2 & 0x8000): continue
    rd = (h2 >> 8) & 0xf; lo = imm16(h1, h2)
    for k in range(4, 28, 2):
        if o + k + 4 > fs: break
        g1, g2 = struct.unpack_from("<HH", d, off + o + k)
        if (g1 & 0xfbf0) == 0xf2c0 and not (g2 & 0x8000) and ((g2 >> 8) & 0xf) == rd:
            v = (imm16(g1, g2) << 16) | lo
            if (v & ~1) in T:
                i = bisect.bisect_right(K, va + o) - 1
                print("%08x\t%08x\t%08x\t%s" % (v & ~1, va + o, F[i][0], F[i][1]))
            break
