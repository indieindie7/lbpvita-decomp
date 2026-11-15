import io, re, subprocess, sys
R = "C:/Users/john/Documents/LBPVita/ghidra/work/"
po = {}
for l in io.open(R + "partwriters.tsv", encoding="utf-8").read().split("\n")[1:]:
    p = l.split("\t")
    if len(p) > 4: po[int(p[2], 16)] = p[4]
out = subprocess.run([sys.executable, "-I", sys.argv[1]], capture_output=True, text=True).stdout.split("\n")
secs = [l.split() for l in out if len(l.split()) >= 3 and l.split()[0].isdigit()]
L = io.open(R + "dis_8165ebb0.txt", encoding="utf-8").read().split("\n")
ad = [l.split()[0] if l.strip() else "" for l in L]
rows = []
for i, s in enumerate(secs):
    a = ad.index(s[2]); b = ad.index(secs[i + 1][2]) if i + 1 < len(secs) else len(L)
    seg = L[a:b]
    offs = []
    for l in seg:
        for m in re.finditer(r"\[sl, #(0x[0-9a-f]+|\d+)\]", l):
            if m.group(1) not in offs: offs.append(m.group(1))
        if re.search(r"\[sl\]", l) and "0" not in offs: offs.append("0")
    thr = [m.group(1) for j, l in enumerate(seg) for m in [re.search(r" cmp\s+r\d, #(0x[0-9a-f]+|\d+)", l)] if m and j > 0 and "#0x188]" in " ".join(seg[max(0, j - 3):j])]
    calls = s[3:]
    part = "/".join(po.get(int(o, 0), "?" + o) for o in offs)
    rows.append((s[0], s[2], ",".join(offs), part, ",".join(thr), " ".join(calls)))
    print("\t".join(rows[-1]))
io.open(sys.argv[2], "w", encoding="utf-8", newline="\n").write("file_bit\ttest_addr\tthing_slot\tpart\tmin_parts_revision\tcalls\n" + "".join("\t".join(r) + "\n" for r in rows))
