# lamskey.py <eboot.elf> <out.tsv> [dump.c ...]
# Translation key hash (text keys passed to 0x8123b858). Checked 11-14: TG_Yes = 0x9d9c76e9,
# TG_No = 0x56eda7e1, SAVE_MESSAGE_MOVE_FLAG_NOT_SET = 0x7832f029 (constants in 0x81183706).
# Writes hash -> key for every identifier string in the eboot, then lists the constants
# in the given dumps that resolve, with the function they sit in.
import re, sys
M = 0xffffffffffffffff
def lams(k):
    v0 = 0; v1 = 0xC8509800
    for i in range(32, 0, -1):
        v0 = (v0 * 0x1b + (ord(k[i-1]) if i-1 < len(k) else 0x20)) & M
    if len(k) > 32:
        v1 = 0
        for i in range(64, 32, -1):
            v1 = (v1 * 0x1b + (ord(k[i-1]) if i-1 < len(k) else 0x20)) & M
    return (v0 + v1 * 0xDEADBEEF) & 0xffffffff
if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read()
    S = sorted(set(m.group().decode() for m in re.finditer(rb"[A-Za-z][A-Za-z0-9_]{2,63}", d)))
    T = {}
    for s in S: T.setdefault(lams(s), s)
    with open(sys.argv[2], "w", newline="\n") as f:
        for h in sorted(T): f.write("0x%08x\t%s\n" % (h, T[h]))
    print("keys", len(T))
    for p in sys.argv[3:]:
        cur = "?"
        for line in open(p, encoding="utf-8", errors="replace"):
            m = re.match(r"// ==== (\S+)", line)
            if m: cur = m.group(1); continue
            for c in re.findall(r"8123b858\((0x[0-9a-f]{6,8})", line):
                v = int(c, 16)
                print("%s\t%s\t%s\t%s" % (p.replace("\\", "/").split("/")[-1], cur, c, T.get(v, "?")))
