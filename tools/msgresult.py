# Messaging_OnMessageResult 0x81070a6c: tbh table -> per message type: case address, calls made (named), key hashes
import struct, re, sys, subprocess, collections
R = "C:/Users/john/Documents/LBPVita/"
d = open(R + "bin/eboot.elf", "rb").read()
phoff = struct.unpack_from("<I", d, 0x1c)[0]; phes, phn = struct.unpack_from("<HH", d, 0x2a)
def off(v):
    for i in range(phn):
        t, o, va, pa, fs, ms = struct.unpack_from("<IIIIII", d, phoff + i * phes)
        if t == 1 and va <= v < va + fs: return o + v - va
nm = {}
for l in open(R + "ghidra/work/funcinfo_named.tsv", encoding="utf-8"):
    f = l.split()
    if len(f) > 2 and f[0] == "F": nm[int(f[1], 16)] = f[2]
keys = {}
for l in open(R + "ghidra/work/lamskeys.tsv", encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) > 1:
        try: keys[int(f[0], 16)] = f[1]
        except ValueError: pass
base = 0x81070a9e; n = 0x59; end = 0x81072078
case = {i + 1: base + 2 * struct.unpack_from("<H", d, off(base + i * 2))[0] for i in range(n)}
starts = sorted(set(case.values()) | {end})
out = subprocess.run([sys.executable, "-I", R + "tools/dis.py", R + "bin/eboot.elf", hex(base + 2 * n), hex(end)], capture_output=True, text=True).stdout
ins = []
for l in out.splitlines():
    f = l.split(None, 2)
    if len(f) >= 2:
        try: ins.append((int(f[0], 16), f[1], f[2] if len(f) > 2 else ""))
        except ValueError: pass
info = collections.defaultdict(lambda: ([], []))
lo = {}
for a, m, o in ins:
    s = max([x for x in starts if x <= a], default=None)
    if s is None: continue
    if m in ("bl", "blx") and "#0x" in o:
        t = int(o.split("#")[1], 16); info[s][0].append(nm.get(t, "%08x" % t))
    mm = re.match(r"(\w+), #(0x[0-9a-f]+|\d+)", o)
    if m == "movw" and mm: lo[mm.group(1)] = int(mm.group(2), 0)
    if m == "movt" and mm and mm.group(1) in lo:
        v = (int(mm.group(2), 0) << 16) | lo[mm.group(1)]
        if v in keys: info[s][1].append(keys[v])
        elif 0x81800000 <= v < 0x81c00000: info[s][1].append("@%08x" % v)
with open(R + "ghidra/work/msgresult.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("type\tcase\tcalls\tkeys_and_data\n")
    for t in sorted(case):
        c, k = info[case[t]]
        f.write("0x%02x\t%08x\t%s\t%s\n" % (t, case[t], " ".join(dict.fromkeys(c)), " ".join(dict.fromkeys(k))))
g = collections.defaultdict(list)
for t, a in case.items(): g[a].append(t)
print(len(g), "distinct cases")
for a in sorted(g):
    c, k = info[a]
    print("%08x types %s | %s | %s" % (a, ",".join("%x" % x for x in g[a]), " ".join(dict.fromkeys(c))[:150], " ".join(dict.fromkeys(k))[:60]))
