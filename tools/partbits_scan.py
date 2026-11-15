import io, re
R = "C:/Users/john/Documents/LBPVita/ghidra/work/"
pn = {int(p[0]): p[4] for p in [l.split("\t") for l in io.open(R + "partwriters.tsv", encoding="utf-8").read().split("\n")[1:] if l]}
L = [l.split(None, 2) for l in io.open(R + "dis_8165ebb0.txt", encoding="utf-8").read().split("\n") if l.strip()]
reg = {}; slot = {}; cur = None; out = []; lastt = None
NOD = ("cmp", "tst", "str", "push", "cb", "b", "it", "pop", "vstr", "nop")
for f in L:
    if len(f) < 2: continue
    a, op = f[0], f[1]; args = [x.strip() for x in (f[2] if len(f) > 2 else "").split(",")]
    opb = op.replace(".w", "")
    m = re.search(r"\[sp, #(0x[0-9a-f]+)\]", f[2] if len(f) > 2 else "")
    if opb == "movs" and len(args) == 2 and args[1].startswith("#"):
        v = int(args[1][1:], 0)
        if v and v & (v - 1) == 0: reg[args[0]] = v.bit_length() - 1
        else: reg.pop(args[0], None)
    elif opb == "ldrd" and m:
        if m.group(1) in slot: reg[args[0]] = slot[m.group(1)]
        else: reg.pop(args[0], None)
        reg.pop(args[1], None)
    elif opb == "strd" and m:
        if args[0] in reg: slot[m.group(1)] = reg[args[0]]
    elif opb == "lsls" and len(args) == 3 and args[2].startswith("#"):
        if args[1] in reg: reg[args[0]] = reg[args[1]] + int(args[2][1:], 0)
        else: reg.pop(args[0], None)
    elif opb in ("ands", "and"):
        srcs = args[1:] if len(args) == 3 else args
        imm = [x for x in srcs if x.startswith("#")]
        b = None
        if imm:
            v = int(imm[0][1:], 0); b = v.bit_length() - 1 if v and v & (v - 1) == 0 else None
        else:
            k = [reg[x] for x in srcs if x in reg]
            b = k[0] if k else None
        if b is not None and b != lastt:
            cur = [b, a, []]; out.append(cur); lastt = b
        if len(args) == 3 or not imm: reg.pop(args[0], None)
    elif opb == "bl":
        mm = re.match(r"#?(?:0x)?(816[0-6][0-9a-f]{4})", args[0])
        if mm and cur: cur[2].append(mm.group(1))
        for r in ("r0", "r1", "r2", "r3", "ip", "lr"): reg.pop(r, None)
    elif not opb.startswith(NOD) and args and args[0] in reg:
        reg.pop(args[0], None)
for b, a, c in out: print(b, pn.get(b, "?"), a, " ".join(c))
print(len(out))
