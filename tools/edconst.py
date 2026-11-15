"""edconst.py: facts table of a DumpDecomp file, no model: per function the float literals, strings, case labels,
compared immediates and the field offsets of the first parameter.
usage: py -3.13 -I tools/edconst.py <dump.c> <out.md>
"""
import io, re, sys, collections

HEAD = re.compile(r"^// ==== (\S+) @ (\S+) body=(\d+)", re.M)
N = chr(10)
PAT = [
    ("floats", re.compile(r"(?<![\w.])(\d+\.\d+(?:e[-+]?\d+)?)(?![\w.])")),
    ("strings", re.compile(r'"((?:[^"\\]|\\.){3,60})"')),
    ("cases", re.compile(r"\bcase (0x[0-9a-f]+|\d+):")),
    ("compares", re.compile(r"(?:==|!=|<=|>=|<|>) (0x[0-9a-f]+|\d+)\b")),
    ("p1 fields", re.compile(r"param_1 \+ (0x[0-9a-f]+)\b")),
]


def top(found, n=24):
    c = collections.Counter(found)
    return ", ".join("%s%s" % (k, "" if v == 1 else " x%d" % v) for k, v in c.most_common(n))


def facts(body):
    out = []
    for label, rx in PAT:
        f = rx.findall(body)
        if f: out.append("  - %s: %s" % (label, top(f)))
    return out


def main():
    t = io.open(sys.argv[1], encoding="utf-8", errors="replace").read()
    ms = list(HEAD.finditer(t))
    with io.open(sys.argv[2], "w", encoding="utf-8", newline=N) as o:
        for i, m in enumerate(ms):
            body = t[m.end():(ms[i + 1].start() if i + 1 < len(ms) else len(t))]
            o.write(N.join(["- 0x%s %s (%s bytes)" % (m.group(2), m.group(1), m.group(3))] + facts(body)) + N)
    print(len(ms))


main()
