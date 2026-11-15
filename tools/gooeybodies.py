# gooeybodies.py <decomp dump> <out.tsv>: per Gooey Do* body: widget getter(size), calls in order, gooey result stores
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
out = ["body\tname\twidget_getter(size)\tcalls_in_order\tgooey_stores\n"]; getters = {}
for m in re.finditer(r"// ==== (\S+) @ ([0-9a-f]{8}) size=\d+\n(.*?)(?=// ==== |\Z)", src, re.S):
    name, addr, body = m.group(1), m.group(2), re.sub(r"\s+", " ", m.group(3))
    i = body.find("{"); code = body[i:]
    g = re.findall(r"(\w+_8170[0-9a-f]{4})\(\w+,(0x[0-9a-f]+|\d+)\)", code)
    for fn, sz in g: getters.setdefault(fn, set()).add(sz)
    calls = [c for c in re.findall(r"\b((?:lbp_|Gooey|Text_)\w+)\(", code)]
    seen = []; [seen.append(c) for c in calls if c not in seen]
    st = re.findall(r"\*\((\w+) \*\)\((param_\d+) \+ (0x2[0-9a-f]{2})\) = ([^;]{1,60});", code)
    out.append("%s\t%s\t%s\t%s\t%s\n" % (addr, name, " ".join("%s(%s)" % x for x in g), " ".join(seen), " | ".join("+%s %s = %s" % (o, t, v) for t, p, o, v in st)))
io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write("".join(out))
for k in sorted(getters): print(k, sorted(getters[k]))
