import sys, struct, bisect
d = open(sys.argv[1], "rb").read()
F = []
for l in open(sys.argv[2], encoding="utf-8", errors="replace"):
    p = l.split()
    if p and p[0] == "F": F.append((int(p[1], 16), p[2]))
F.sort(); K = [a for a, _ in F]
def nm(v):
    i = bisect.bisect_right(K, v & ~1) - 1
    return F[i][1] if i >= 0 and F[i][0] == (v & ~1) else "?"
for t in sys.argv[3:]:
    w = struct.pack("<I", int(t, 16) | 1); o = -1
    while True:
        o = d.find(w, o + 1)
        if o < 0: break
        if o % 4: continue
        b = o - 0x40
        print("word %s at file 0x%x:" % (t, o))
        for q in range(o - 0x18, o + 0x1c, 4):
            v = struct.unpack_from("<I", d, q)[0]
            print("   %+d  %08x %s" % ((q - o), v, nm(v) if 0x81000000 <= v < 0x81800000 else ""))
