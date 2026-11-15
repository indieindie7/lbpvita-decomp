# clsstr.py <vtables.tsv> <classes.tsv> <funcinfo.tsv> <out.txt>
# For each unnamed class (cls_*): strings used by its own virtual functions. Helps to pick class names.
import sys, io, collections
vt, cl, fi, out = sys.argv[1:5]
strs = collections.defaultdict(list); cur = None
for l in io.open(fi, encoding="utf-8", errors="replace"):
    p = l.rstrip("\n").split("\t") if "\t" in l else l.rstrip("\n").split(" ", 1)
    if p[0] == "F": cur = l.split()[2]
    elif p[0] == "S" and cur: strs[cur].append(l.rstrip("\n")[2:].strip())
slots = {}
for l in io.open(vt, encoding="utf-8"):
    p = l.rstrip("\n").split("\t")
    slots[p[0]] = p[4].split(" ")
o = io.open(out, "w", encoding="utf-8", newline="\n"); n = 0
for l in io.open(cl, encoding="utf-8"):
    p = l.rstrip("\n").split("\t")
    if not p[1].startswith("cls_") or len(p) < 6 or not p[5]: continue
    seen = []
    for i in p[5].split(","):
        f = slots[p[0]][int(i)] if int(i) < len(slots[p[0]]) else None
        for s in strs.get(f, []):
            if s not in seen: seen.append(s)
    if seen:
        o.write("%s base=%s : %s\n" % (p[0], p[3], " | ".join(seen)[:1500])); n += 1
print("classes with strings", n)
