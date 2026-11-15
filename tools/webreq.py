# webreq.py <eboot.elf> : web request type (1..0x11) -> case address -> URL strings, from the tbh switch at 0x81147bc4
import sys, struct, re, capstone
f = open(sys.argv[1], "rb").read()
B = 0x81000000 - 0x80
T = 0x81147bc8; END = 0x811488d0
tg = [T + 2 * struct.unpack_from("<H", f, T - B + 2 * i)[0] for i in range(17)]
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB); md.skipdata = True
def cstr(va):
    o = va - B
    if not (0 <= o < len(f)): return None
    e = f.find(b"\0", o); s = f[o:e]
    if 1 < len(s) < 60 and all(32 <= c < 127 for c in s): return s.decode()
    return None
srt = sorted(set(tg)) + [END]
print("type\tcase\tstrings")
for i, t in enumerate(tg):
    nxt = srt[srt.index(t) + 1]; lo = {}; out = []
    for ins in md.disasm(f[t - B:nxt - B], t):
        m = re.match(r"(\w+), #(0x[0-9a-f]+|\d+)$", ins.op_str)
        if not m: continue
        if ins.mnemonic.startswith("movw"): lo[m.group(1)] = int(m.group(2), 0)
        elif ins.mnemonic.startswith("movt") and m.group(1) in lo:
            s = cstr((int(m.group(2), 0) << 16) | lo.pop(m.group(1)))
            if s and (s[0] in "/?" ) and s not in out: out.append(s)
    print("0x%x\t%08x\t%s" % (i + 1, t, " ".join(out)))
