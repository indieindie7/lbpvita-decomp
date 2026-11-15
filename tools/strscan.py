# strscan.py <eboot.elf> <funcinfo.tsv> <offset hex...> : every Thumb-2 STR.W / LDR.W / ADD.W with
# a 12-bit immediate equal to offset (str rt,[rn,#off]), with the function that holds it.
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
    k = h1 & 0xfff0
    if k == 0xf8c0: kind = "str"
    elif k == 0xf8d0: kind = "ldr"
    else: continue
    imm = h2 & 0xfff
    if imm in T:
        i = bisect.bisect_right(K, va + o) - 1
        print("%03x %s r%d,[r%d] %08x in %08x %s" % (imm, kind, h2 >> 12, h1 & 15, va + o, F[i][0], F[i][1]))
