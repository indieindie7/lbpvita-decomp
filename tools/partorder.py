# partorder.py <decomp dump> <partfields.tsv> <out.tsv>: per part body, the saved items in code order
# (inline u32 / u8 reads of part + offset, and sub-writer calls on part + offset). Loop / condition reads are listed too.
import io, re, sys
src = io.open(sys.argv[1], encoding="utf-8").read()
funcs = {}
for m in re.finditer(r"// ==== (\S+) @ ([0-9a-f]{8}) size=\d+\n(.*?)(?=// ==== |\Z)", src, re.S):
    funcs[m.group(2)] = re.sub(r"\s+", " ", m.group(3))
pat = re.compile(r"= \*\((\w+) \*\)\(param_2 \+ (0x[0-9a-f]+|\d+)\);|= \*param_2;|(\w+)\(param_1,\(?[\w \*]*\)?\(?param_2(?: \+ (0x[0-9a-f]+|\d+))?\)?((?:,[^;()]*)?)\)")
out = ["part\tseq\tkind\toffset\textra\n"]; tot = 0
for l in io.open(sys.argv[2], encoding="utf-8").read().split("\n")[1:]:
    f = l.split("\t")
    if len(f) < 3 or f[2] not in funcs: continue
    n = 0
    for m in pat.finditer(funcs[f[2]]):
        if m.group(3):
            if m.group(3) in ("Stream_Grow",): continue
            kind = m.group(3); off = int(m.group(4) or "0", 0); ex = m.group(5).lstrip(",")[:60]
        else:
            t = m.group(1) or "uint"; kind = "u8" if t in ("undefined1", "byte", "char") else "u16" if t in ("ushort", "undefined2", "short") else "u32"
            off = int(m.group(2) or "0", 0); ex = ""
        out.append("%s\t%d\t%s\t0x%x\t%s\n" % (f[0], n, kind, off, ex)); n += 1
    tot += n
io.open(sys.argv[3], "w", encoding="utf-8", newline="\n").write("".join(out))
print("items", tot)
