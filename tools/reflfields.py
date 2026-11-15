# reflfields.py <decomp dump> <partorder.tsv> <out.tsv> : text-reflect functions -> field name, offset, type code; guesses the part by offset overlap with partorder.tsv
import io, re, sys, collections
src = io.open(sys.argv[1], encoding="utf-8").read()
order = collections.defaultdict(set)
for l in io.open(sys.argv[2], encoding="utf-8").read().split("\n")[1:]:
    f = l.split("\t")
    if len(f) >= 4 and f[3].startswith("0x"): order[f[0]].add(int(f[3], 16))
pat = re.compile(r"\"([A-Za-z_][\w\.\[\]]*)\" ?, ?\(?[\w \*]*\)?\(?param_2(?: \+ (0x[0-9a-f]+|\d+))?\)?, ?(0x[0-9a-f]+|\d+)")
rows = []; nf = 0
for m in re.finditer(r"// ==== (\S+) @ ([0-9a-f]{8}) size=\d+\n(.*?)(?=// ==== |\Z)", src, re.S):
    body = re.sub(r"\s+", " ", m.group(3))
    fl = [(x.group(1), int(x.group(2) or "0", 0), int(x.group(3), 0)) for x in pat.finditer(body)]
    if not fl: continue
    nf += 1; offs = set(o for _, o, _ in fl); best = ("", 0.0)
    for p, s in order.items():
        if len(s) < 3: continue
        sc = len(s & offs) / float(len(s | offs))
        if sc > best[1]: best = (p, sc)
    part = "%s(%.2f)" % best if best[1] >= 0.5 else "-"
    for n, o, t in fl: rows.append("%s\t%s\t%s\t%s\t0x%x\t0x%x\n" % (m.group(2), m.group(1), part, n, o, t))
io.open(sys.argv[3], "w", encoding="utf-8", newline="\n").write("func\tfunc_name\tpart_guess\tfield\toffset\ttype\n" + "".join(rows))
print("functions", nf, "fields", len(rows))
