# immscan.py <eboot.elf> <funcinfo.tsv> <imm hex...> : Thumb-2 movw / addw / add.w(modified imm, simple) with this immediate, per function
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
    kind = None
    if (h1 & 0xfbf0) == 0xf240 and not (h2 & 0x8000): kind = "movw"
    elif (h1 & 0xfbf0) == 0xf200 and not (h2 & 0x8000): kind = "addw"
    if not kind: continue
    imm = ((h1 & 0xf) << 12 if kind == "movw" else 0) | (((h1 >> 10) & 1) << 11) | (((h2 >> 12) & 7) << 8) | (h2 & 0xff)
    if imm in T:
        i = bisect.bisect_right(K, va + o) - 1
        print("%04x %s %08x in %08x %s" % (imm, kind, va + o, F[i][0], F[i][1]))
