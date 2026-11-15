"""edscope.py: editor scope table. Walks callees from editor-named functions and lists the unnamed ones.
usage: py -3.13 -I tools/edscope.py ghidra/work/funcinfo_named.tsv ghidra/work/edscope.tsv [depth=2] [minratio=0.5]
out columns: addr name size depth seed edcallers allcallers ratio   (ratio = edcallers / allcallers; low = shared utility)
"""
import io, re, sys, collections

SEED = re.compile(r"^(Poppet_|Undo_)|Stamp|Glue|Slice|Sticker|Decorat|Tweak|Vertex|Joint|Cursor|Lasso|Inventory|"
                  r"EditMode|EditState|GridS|AngleSnap|FrontView|PreviewMode|Corner|Paint|Emitter|Capture|Clone|Select")
SKIP = re.compile(r"^(Reflect|ReflectText|Text_|Gooey)")


def load(path):
    F = {}; C = collections.defaultdict(list); cur = None
    for l in io.open(path, encoding="utf-8", errors="replace"):
        f = l.split()
        if len(f) >= 5 and f[0] == "F":
            cur = f[1]; F[cur] = (f[2], f[3], int(f[4]))
        elif len(f) == 2 and f[0] == "C" and cur:
            C[cur].append(f[1])
    return F, C


def build_callers(F, C):
    callers = collections.defaultdict(set)
    for a, cs in C.items():
        for c in cs:
            if c in F: callers[c].add(a)
    return callers


def edratio(a, callers, dist):
    cl = callers[a]; ed = sum(1 for x in cl if x in dist)
    return ed, len(cl), ed / max(1, len(cl))


def walk(F, C, callers, seeds, depth, minratio):
    """callee walk; does not pass through shared utilities (most callers must already be in scope)"""
    dist = {a: (0, a) for a in seeds}; front = list(seeds)
    for d in range(1, depth + 1):
        nxt = []
        for a in front:
            for c in C.get(a, ()):
                if c in F and c not in dist and edratio(c, callers, dist)[2] >= minratio:
                    dist[c] = (d, dist[a][1]); nxt.append(c)
        front = nxt
    return dist


def table(F, callers, dist):
    rows = []
    for a, (d, seed) in dist.items():
        n, s, z = F[a]
        if s != "USER_DEFINED" and d:
            rows.append((a, n, z, d, F[seed][0]) + edratio(a, callers, dist))
    rows.sort(key=lambda r: (r[3], -r[7], -r[2]))
    return rows


def main():
    src, out = sys.argv[1], sys.argv[2]
    depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    minratio = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    F, C = load(src); callers = build_callers(F, C)
    seeds = [a for a, (n, s, z) in F.items() if s == "USER_DEFINED" and SEED.search(n) and not SKIP.match(n)]
    dist = walk(F, C, callers, seeds, depth, minratio); rows = table(F, callers, dist)
    T, N = chr(9), chr(10)
    with io.open(out, "w", encoding="utf-8", newline=N) as o:
        o.write(T.join("addr name size depth seed edcallers allcallers ratio".split()) + N)
        for r in rows: o.write(T.join(["%s", "%s", "%d", "%d", "%s", "%d", "%d", "%.2f"]) % r + N)
    bd = collections.Counter(r[3] for r in rows)
    print("seeds %d  scope %d  unnamed %d  by depth %s  bytes %d" % (len(seeds), len(dist), len(rows), dict(bd), sum(r[2] for r in rows)))


main()
