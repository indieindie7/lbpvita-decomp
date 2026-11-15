import sys, struct, bisect, collections
d = open(sys.argv[1], "rb").read()
off, va, fs = 0x80, 0x81000000, None
phoff = struct.unpack_from("<I", d, 0x1c)[0]; phes, phnum = struct.unpack_from("<HH", d, 0x2a)
for i in range(phnum):
    t, o, v, pa, fsz, ms, fl, al = struct.unpack_from("<8I", d, phoff + i * phes)
    if t == 1 and fl & 1 and fs is None: off, va, fs = o, v, fsz
F = []
for l in open(sys.argv[2], encoding="utf-8", errors="replace"):
    p = l.split()
    if p and p[0] == "F": F.append((int(p[1], 16), p[2]))
F.sort(); K = [a for a, _ in F]
imm = int(sys.argv[3], 16)
c = collections.Counter()
for o in range(0, fs - 2, 2):
    h = struct.unpack_from("<H", d, off + o)[0]
    if (h & 0xf800) == 0x2800 and (h & 0xff) == imm:
        i = bisect.bisect_right(K, va + o) - 1
        c[(F[i][0], F[i][1])] += 1
for (a, n), k in sorted(c.items()): print("%08x %s %d" % (a, n, k))
