# keyscan.py <eboot.elf> <funcinfo.tsv> <lamskeys.tsv> <out.tsv>
# Finds text key hashes used as constants in code: Thumb-2 movw + movt on the same
# register, movt up to 20 bytes later (kind m) and aligned literal pool words (kind p, a few false hits possible).
# Output: function address, function name, kind, site, hash, key.
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
    if p and p[0] == "F": F.append((int(p[1], 16), p[2], int(p[-1])))
F.sort(); K = [a for a, _, _ in F]
T = {}
for l in open(sys.argv[3], encoding="utf-8"):
    h, k = l.rstrip("\n").split("\t"); T[int(h, 16)] = k
def imm16(h1, h2):
    return ((h1 & 0xf) << 12) | (((h1 >> 10) & 1) << 11) | (((h2 >> 12) & 7) << 8) | (h2 & 0xff)
def owner(a):
    i = bisect.bisect_right(K, a) - 1
    if i < 0 or a >= F[i][0] + F[i][2] + 64: return None
    return F[i]
out = []
end = min(fs, F[-1][0] + F[-1][2] - va)
for o in range(0, end - 24, 2):
    h1, h2 = struct.unpack_from("<2H", d, off + o)
    if (h1 & 0xfbf0) == 0xf240 and (h2 & 0x8000) == 0:
        rd = (h2 >> 8) & 0xf
        for g in range(4, 22, 2):      # movt may sit a few instructions later
            h3, h4 = struct.unpack_from("<2H", d, off + o + g)
            if (h3 & 0xfbf0) == 0xf2c0 and (h4 & 0x8000) == 0 and ((h4 >> 8) & 0xf) == rd:
                v = imm16(h1, h2) | (imm16(h3, h4) << 16)
                if v in T:
                    f = owner(va + o)
                    if f: out.append((f[0], f[1], "m", va + o, v, T[v]))
                break
    if o % 4 == 0:
        v = struct.unpack_from("<I", d, off + o)[0]
        if v in T and v > 0x10000 and not (0x81000000 <= v < 0x82000000):
            f = owner(va + o)
            if f: out.append((f[0], f[1], "p", va + o, v, T[v]))
out.sort()
with open(sys.argv[4], "w", newline="\n") as f:
    for r in out: f.write("%08x\t%s\t%s\t%08x\t0x%08x\t%s\n" % r)
print("hits", len(out), "movw/movt", sum(1 for r in out if r[2] == "m"), "functions", len({r[0] for r in out}))
