import sys, struct, bisect
d = open(sys.argv[1], "rb").read()
phoff = struct.unpack_from("<I", d, 0x1c)[0]; phes, phnum = struct.unpack_from("<HH", d, 0x2a)
fs = None
for i in range(phnum):
    t, o, v, pa, fsz, ms, fl, al = struct.unpack_from("<8I", d, phoff + i * phes)
    if t == 1 and fl & 1 and fs is None: off, va, fs = o, v, fsz
F = []
for l in open(sys.argv[2], encoding="utf-8", errors="replace"):
    p = l.split()
    if p and p[0] == "F": F.append((int(p[1], 16), p[2]))
F.sort(); K = [a for a, _ in F]
lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
for o in range(0, fs - 8, 2):
    h = struct.unpack_from("<H", d, off + o)[0]
    if (h & 0xf800) == 0x2800 and lo <= (h & 0xff) <= hi:
        for k in range(2, 10, 2):
            a, b = struct.unpack_from("<HH", d, off + o + k)
            if (a & 0xfff0) == 0xe8d0 and (b & 0xffe0) == 0xf000:
                i = bisect.bisect_right(K, va + o) - 1
                print("%08x cmp #0x%x %s in %08x %s" % (va + o, h & 0xff, "tbh" if b & 0x10 else "tbb", F[i][0], F[i][1]))
