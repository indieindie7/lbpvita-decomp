"""edask.py: build one small C file per editor topic from the scoped dump, then let the local model answer a question on it.
usage: py -3.13 -I tools/edask.py <topics.txt> <outdir>
topics.txt lines:  <name> | <regex over seed + draft name + purpose> | <question>
For each topic: writes <outdir>/ask_<name>.c (matching functions of ghidra/work/edscope479.c, biggest first, capped) and runs
Tools/llm/localread.py on it; all answers go to <outdir>/edask_answers.md. No names are applied. GPU: LOCALREAD_GPU=1, no CUDA_VISIBLE_DEVICES.
"""
import io, re, sys, subprocess

W = "ghidra/work/"
HEAD = re.compile(r"^// ==== (\S+) @ (\S+) body=(\d+)", re.M)
CAP = 120000   # characters per topic file
LR = r"C:\Users\john\Documents\Tools\llm\localread.py"
T, N = chr(9), chr(10)


def bodies():
    t = io.open(W + "edscope479.c", encoding="utf-8", errors="replace").read()
    ms = list(HEAD.finditer(t))
    return {m.group(2): t[m.start():(ms[i + 1].start() if i + 1 < len(ms) else len(t))] for i, m in enumerate(ms)}


def rows():
    seed = {l.split(T)[0]: l.split(T)[4] for l in io.open(W + "edscope.tsv", encoding="utf-8")}
    out = []
    for l in io.open(W + "edscope479_draft.tsv", encoding="utf-8").read().split(N)[1:]:
        f = l.split(T)
        if len(f) >= 6: out.append((f[0], seed.get(f[0], ""), f[2], f[5]))
    return out


def build(name, rx, R, B, outdir):
    k = re.compile(rx, re.I)
    hit = sorted((r for r in R if k.search(" ".join(r[1:]))), key=lambda r: -len(B.get(r[0], "")))
    text = ""; n = 0
    for a, seed, draft, purpose in hit:
        part = "// called from: %s; draft purpose (unverified): %s%s%s" % (seed, purpose, N, B.get(a, ""))
        if len(text) + len(part) > CAP: continue
        text += part; n += 1
    p = "%s/ask_%s.c" % (outdir, name)
    io.open(p, "w", encoding="utf-8", newline=N).write(text)
    return p, n, len(hit)


def main():
    topics, outdir = sys.argv[1], sys.argv[2]
    R, B = rows(), bodies()
    with io.open(outdir + "/edask_answers.md", "w", encoding="utf-8", newline=N) as o:
        for l in io.open(topics, encoding="utf-8"):
            f = [x.strip() for x in l.split(" | ")]
            if len(f) != 3: continue
            p, n, total = build(f[0], f[1], R, B, outdir)
            r = subprocess.run([sys.executable, LR, p, f[2], "--keep"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            o.write("## %s (%d of %d functions, %s)%sQ: %s%s%s%s" % (f[0], n, total, p, N, f[2], N, r.stdout.strip() or ("FAILED: " + r.stderr[-300:]), N + N)); o.flush()
            print(f[0], n, total, len(r.stdout), flush=True)


main()
