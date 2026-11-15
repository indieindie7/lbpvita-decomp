# partfields.py <decomp dump> <partfields.tsv> <out.tsv>: per part body, each saved field: offset in the part, field writer, name
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
funcs = {}
for m in re.finditer(r"// ==== (\S+) @ ([0-9a-f]{8}) size=\d+\n(.*?)(?=// ==== |\Z)", src, re.S):
    funcs[m.group(2)] = re.sub(r"\s+", " ", m.group(3))
out = ["part\toffset\tfield_writer\tfield\n"]; tot = 0
for l in io.open(sys.argv[2], encoding="utf-8").read().split("\n")[1:]:
    f = l.split("\t")
    if len(f) < 3: continue
    body = funcs.get(f[2])
    if body is None: print("missing", f[0], f[2]); continue
    n = 0
    for m in re.finditer(r"(\w+)\(param_1,([^;]*?),\"([^\"]+)\"\)", body):
        arg = m.group(2).strip()
        mm = re.fullmatch(r"\(?[\w \*]*\)?\(?param_2(?: \+ (0x[0-9a-f]+|\d+))?\)?", arg)
        off = ("0x%x" % int(mm.group(1) or "0", 0)) if mm else "?(%s)" % arg[:40]
        w = m.group(1); a = re.search(r"([0-9a-f]{8})$", w)
        out.append("%s\t%s\t%s\t%s\n" % (f[0], off, w, m.group(3))); n += 1
    tot += n
    if n == 0: out.append("%s\t-\t-\t(no named fields)\n" % f[0])
io.open(sys.argv[3], "w", encoding="utf-8", newline="\n").write("".join(out))
print("fields", tot)
