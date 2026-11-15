"""edflow.py: call skeleton per editor topic, from the call table only (no code reading, no model).
usage: py -3.13 -I tools/edflow.py <topics.txt> <out.md> [maxfan=40]
topics.txt lines:  <name> | <regex> | <question>   (the regex is matched against hand names here)
For every hand-named function that matches the topic: its callees in call order (repeats dropped), each with
address + name; unnamed callees carry the local model's draft purpose (edscope479_draft.tsv, unverified).
Callees with more than maxfan callers are shared utilities and are left out (count shown).
"""
import io, re, sys, collections

W = "ghidra/work/"
T, N = chr(9), chr(10)


def load(path):
    F = {}; C = collections.defaultdict(list); cur = None
    for l in io.open(path, encoding="utf-8", errors="replace"):
        f = l.split()
        if len(f) >= 5 and f[0] == "F":
            cur = f[1]; F[cur] = (f[2], f[3], int(f[4]))
        elif len(f) == 2 and f[0] == "C" and cur:
            C[cur].append(f[1])
    return F, C


def fan(C):
    n = collections.Counter()
    for a, cs in C.items():
        for c in set(cs): n[c] += 1
    return n


def drafts():
    d = {}
    for l in io.open(W + "edscope479_draft.tsv", encoding="utf-8").read().split(N)[1:]:
        f = l.split(T)
        if len(f) >= 6: d[f[0]] = "%s? %s" % (f[2], f[5])
    return d


def callee_line(c, F, D):
    name, src, size = F[c]
    if src == "USER_DEFINED": return "  - 0x%s %s" % (c, name)
    return "  - 0x%s (unnamed, %d bytes) draft: %s" % (c, size, D.get(c, "-"))


def section(a, F, C, nfan, D, maxfan):
    seen = []; util = 0
    for c in C.get(a, ()):
        if c not in F or c in seen or c == a: continue
        if nfan[c] > maxfan: util += 1; continue
        seen.append(c)
    head = "- 0x%s %s (%d bytes, %d callers, %d shared utility calls left out)" % (a, F[a][0], F[a][2], nfan[a], util)
    return N.join([head] + [callee_line(c, F, D) for c in seen])


def main():
    topics, out = sys.argv[1], sys.argv[2]
    maxfan = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    F, C = load(W + "funcinfo_named.tsv"); nfan = fan(C); D = drafts()
    with io.open(out, "w", encoding="utf-8", newline=N) as o:
        for l in io.open(topics, encoding="utf-8"):
            f = [x.strip() for x in l.split(" | ")]
            if len(f) != 3: continue
            k = re.compile(f[1])
            hit = sorted(a for a, v in F.items() if v[1] == "USER_DEFINED" and k.search(v[0]))
            o.write("## %s (%d hand-named functions)%s" % (f[0], len(hit), N))
            o.write(N.join(section(a, F, C, nfan, D, maxfan) for a in hit) + N + N)
            print(f[0], len(hit), flush=True)


main()
