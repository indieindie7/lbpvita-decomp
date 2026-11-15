# revgates.py <decomp dump> <partfields.tsv> <out.tsv> : revision gates of the binary serialisers.
# stream +0x54 = head revision, +0x58 = branch word (high 16 = 0x4431 "D1" Vita branch, low 16 = branch revision).
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
part = {}
for l in io.open(sys.argv[2], encoding="utf-8").read().split("\n")[1:]:
    f = l.split("\t")
    if len(f) >= 3:
        for a in f[1:3]:
            if a.strip(): part.setdefault(a.strip(), f[0])
H = r"\*\(uint \*\)\(param_1 \+ 0x54\)"; B = r"\*\(uint \*\)\(param_1 \+ 0x58\)"
rows = []; nf = 0
for m in re.finditer(r"// ==== (\S+) @ ([0-9a-f]{8}) size=\d+\n(.*?)(?=// ==== |\Z)", src, re.S):
    body = re.sub(r"\s+", " ", m.group(3))
    hv = set(re.findall(r"(\w+) = " + H + r"[;,)]", body)); bv = set(re.findall(r"(\w+) = " + B + r" & 0xffff[;,)]", body))
    t = re.sub(B + r" >> 0x10 == 0x4431", "VITA", body)
    t = re.sub(B + r" >> 0x10 != 0x4431", "!VITA", t)
    t = re.sub(r"\(" + B + r" & 0xffff\)", "br", t); t = re.sub(B + r" & 0xffff", "br", t); t = re.sub(H, "head", t)
    for v in hv: t = re.sub(r"\b%s\b" % v, "head", t)
    for v in bv: t = re.sub(r"\b%s\b" % v, "br", t)
    seq = 0; i = 0
    while True:
        i = t.find("if (", i)
        if i < 0: break
        j = i + 3; d = 0
        while j < len(t):
            if t[j] == "(": d += 1
            elif t[j] == ")":
                d -= 1
                if d == 0: break
            j += 1
        cond = t[i + 4:j]; i = j
        if not re.search(r"\b(head|br|VITA)\b", cond): continue
        if "param_1 + 0x68" in cond: continue
        cond = re.sub(r"br = br, ?", "", cond); cond = re.sub(r"head = head, ?", "", cond)
        while True:
            c2 = re.sub(r"\(([^()]*)\)", lambda x: x.group(1) if re.fullmatch(r"[\w !<>=]+", x.group(1)) and ("&&" not in x.group(1) and "||" not in x.group(1)) else "[" + x.group(1) + "]", cond)
            if c2 == cond: break
            cond = c2
        cond = cond.replace("[", "(").replace("]", ")")
        nxt = t[j + 1:j + 400]; nxt = re.sub(r"^\s*\{\s*", "", nxt); st = nxt.split(";")[0][:110]
        s = re.search(r"\"(\w[\w\.]*)\"", st); o = re.search(r"(?:param_2|local_\w+|\w+Var\d+) \+ (0x[0-9a-f]+|\d+)", st)
        rows.append("%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\n" % (m.group(2), m.group(1), part.get(m.group(2), "-"), seq, cond, s.group(1) if s else "", o.group(1) if o else "", st))
        seq += 1
    if seq: nf += 1
io.open(sys.argv[3], "w", encoding="utf-8", newline="\n").write("func\tfunc_name\tpart\tseq\tgate\tfield_string\tfirst_offset\tfirst_statement\n" + "".join(rows))
print("functions", nf, "gates", len(rows))
