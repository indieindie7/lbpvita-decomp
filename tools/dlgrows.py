# dlgrows.py <dis.py dump of 0x8106e632..0x81070088> <out.tsv> : replays the straight-line init of the dialog type table DAT_818d354c (0x60 bytes per dialog type)
import io, re, sys, struct
reg = {}; base = {}; out = {}; unk = 0
BASE = 0x818d354c
def val(s):
    s = s.strip()
    if s.startswith("#"): return int(s[1:], 0)
    return reg.get(s)
for l in io.open(sys.argv[1], encoding="utf-8"):
    m = re.match(r"([0-9a-f]{8}) (\S+)\s+(.*)", l.strip())
    if not m: continue
    a, op, args = m.group(1), m.group(2), m.group(3)
    op0 = op.split(".")[0]
    p = [x.strip() for x in re.split(r",(?![^\[]*\])", args)]
    if op0 in ("movs", "mov", "movw", "mvn", "mvns"):
        v = val(p[1])
        if v is not None and op0.startswith("mvn"): v = ~v & 0xffffffff
        reg[p[0]] = v
    elif op0 == "movt":
        if reg.get(p[0]) is not None: reg[p[0]] = (reg[p[0]] & 0xffff) | (int(p[1][1:], 0) << 16)
    elif op0 in ("add", "adds", "addw", "sub", "subs", "subw") and len(p) == 3:
        x, y = val(p[1]), val(p[2])
        reg[p[0]] = None if x is None or y is None else ((x + y) if op0.startswith("add") else (x - y)) & 0xffffffff
    elif op0 in ("add", "adds", "sub", "subs") and len(p) == 2:
        x, y = val(p[0]), val(p[1])
        reg[p[0]] = None if x is None or y is None else ((x + y) if op0.startswith("add") else (x - y)) & 0xffffffff
    elif op0 in ("str", "strb", "strh", "strd"):
        mm = re.match(r"\[(\w+)(?:, (#?-?\w+))?\]", p[-1])
        if not mm: unk += 1; continue
        b = reg.get(mm.group(1)); o = val(mm.group(2)) if mm.group(2) else 0
        srcs = p[:-1]
        if b is None or o is None: unk += 1; continue
        for k, s in enumerate(srcs):
            v = reg.get(s); ad = (b + o + 4 * k) & 0xffffffff
            out[ad] = (op0, v, a)
    elif op0 in ("ldr", "ldrb", "ldrh", "pop", "bl", "blx", "vmov", "vldr"):
        if op0.startswith("ldr") : reg[p[0]] = None
        if op0 in ("bl", "blx"):
            for r in ("r0", "r1", "r2", "r3", "ip", "lr"): reg[r] = None
    elif op0 in ("push", "vstr", "bx", "b", "nop", "cmp", "it", "vpush", "vpop"): pass
    else:
        if p and p[0] in reg: reg[p[0]] = None
rows = {}
for ad in sorted(out):
    if not (BASE <= ad < BASE + 0x4000): continue
    r, f = divmod(ad - BASE, 0x60)
    rows.setdefault(r, []).append((f, out[ad]))
print("unk stores", unk, "stores", len(out), "rows", len(rows), "max", max(rows) if rows else None)
w = io.open(sys.argv[2], "w", encoding="utf-8", newline="\n"); w.write("row\taddr\tfields(off=op:value)\n")
for r in sorted(rows):
    w.write("%d\t%08x\t%s\n" % (r, BASE + r * 0x60, " ".join("%x=%s:%s" % (f, o[0][3:] or "w", "?" if o[1] is None else "0x%x" % o[1]) for f, o in rows[r])))
others = sorted(ad for ad in out if not (BASE <= ad < BASE + 0x4000))
print("other", len(others), ["%08x" % x for x in others[:20]])
