# dialogs.py <elf> <funcinfo> <lamskeys> <out.tsv>: per call of Messaging_OpenDialog 0x8107075e: dialog type (r1) and the text keys translated before it
import sys, io, re, subprocess, collections
elf, fi, lk, out = sys.argv[1:5]
OPEN = "8107075e"; TR = "8123b858"
keys = {}
for l in io.open(lk, encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 2: keys[int(f[0], 16)] = f[1]
funcs = []; calls = collections.defaultdict(list); cur = None
for l in io.open(fi, encoding="utf-8"):
    f = l.split()
    if len(f) < 2: continue
    if f[0] == "F": cur = (f[1], f[2], int(f[4]) if len(f) > 4 and f[4].isdigit() else 0); funcs.append(cur)
    elif f[0] == "C" and f[1] == OPEN: calls[cur].append(1)
rows = []
for (a, name, size) in funcs:
    if (a, name, size) not in calls: continue
    s = int(a, 16); e = s + max(size, 4) + 2
    txt = subprocess.run([sys.executable, "-I", "tools/dis.py", elf, hex(s), hex(e)], capture_output=True, text=True).stdout
    reg = {}; pend = []; r1 = "?"
    for l in txt.split("\n"):
        m = re.match(r"([0-9a-f]{8}) (\S+)\s+(.*)", l)
        if not m: continue
        ad, op, args = m.groups()
        mm = re.match(r"(r\d+|lr|ip), #(-?0x[0-9a-f]+|-?\d+)$", args)
        if mm and op.startswith("mov") and not op.startswith("movt"):
            reg[mm.group(1)] = int(mm.group(2), 0) & 0xffffffff
        elif mm and op.startswith("movt"):
            reg[mm.group(1)] = (reg.get(mm.group(1), 0) & 0xffff) | ((int(mm.group(2), 0) & 0xffff) << 16)
        elif mm and op.startswith("mvn"):
            reg[mm.group(1)] = (~int(mm.group(2), 0)) & 0xffffffff
        elif op.startswith(("adds", "mov")) and re.match(r"r1, r\d+(, #0)?$", args):
            reg.pop("r1", None)
        elif op == "bl" and args.endswith(TR):
            h = reg.get("r0"); pend.append(keys.get(h, "?%08x" % h if h is not None else "?"))
        elif op == "bl" and args.endswith(OPEN):
            t = reg.get("r1"); rows.append((ad, a, name, "0x%x" % t if t is not None else "?", " ".join(pend))); pend = []
        if op in ("bl", "blx"): reg.pop("r0", None); reg.pop("r1", None) if not args.endswith(TR) else None
io.open(out, "w", encoding="utf-8", newline="\n").write("call\tfunc\tname\ttype\tkeys translated before the call (in order)\n" + "".join("\t".join(r) + "\n" for r in rows))
c = collections.Counter(r[3] for r in rows)
print(len(rows), "calls;", " ".join("%s:%d" % x for x in sorted(c.items(), key=lambda x: -x[1])))
