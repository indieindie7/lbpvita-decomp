# mvscan.py <elf> <funcinfo> <fileoff|va hex> [span] : functions that load an address in [va, va+span) with movw + movt
import sys, struct, bisect
d = open(sys.argv[1], "rb").read()
phoff = struct.unpack_from("<I", d, 0x1c)[0]; phes, phnum = struct.unpack_from("<HH", d, 0x2a)
segs = []
for i in range(phnum):
    t, o, v, pa, fsz, ms, fl, al = struct.unpack_from("<8I", d, phoff + i * phes)
    if t == 1: segs.append((o, v, fsz, fl))
x = int(sys.argv[3], 16); span = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x10
if x < 0x80000000:
    for o, v, fsz, fl in segs:
        if o <= x < o + fsz: x = x - o + v
print("va %08x" % x)
F = []
for l in open(sys.argv[2], encoding="utf-8", errors="replace"):
    p = l.split()
    if p and p[0] == "F": F.append((int(p[1], 16), p[2]))
F.sort(); K = [a for a, _ in F]
off, va, fs, _ = [s for s in segs if s[3] & 1][0]
def imm16(h1, h2): return ((h1 & 0xf) << 12) | (((h1 >> 10) & 1) << 11) | (((h2 >> 12) & 7) << 8) | (h2 & 0xff)
for o in range(0, fs - 4, 2):
    h1, h2 = struct.unpack_from("<HH", d, off + o)
    if (h1 & 0xfbf0) == 0xf240 and (h2 & 0x8000) == 0:
        rd = (h2 >> 8) & 0xf; lo = imm16(h1, h2)
        for k in range(4, 24, 2):
            g1, g2 = struct.unpack_from("<HH", d, off + o + k)
            if (g1 & 0xfbf0) == 0xf2c0 and (g2 & 0x8000) == 0 and ((g2 >> 8) & 0xf) == rd:
                v = (imm16(g1, g2) << 16) | lo
                if x <= v < x + span:
                    i = bisect.bisect_right(K, va + o) - 1
                    print("%08x loads %08x in %08x %s" % (va + o, v, F[i][0], F[i][1]))
                break
