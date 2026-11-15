"""llmname.py: the local model (Sage, via Tools/llm/localread.py) proposes a name for each function of a DumpDecomp .c file.
usage: py -3.13 tools/llmname.py <dump.c> <out.tsv> [--blind] [--prefixes a,b] [--ctx funcinfo_named.tsv] [--glossary file]
  --ctx     prompt v2: adds the named callers and the string refs of each function (blind mode drops callers that carry the hidden name)
  --blind   test mode: the function's own name and its Hand-named comment are replaced by FUN_<addr>; out.tsv keeps the hand name.
out columns: addr  current  proposed  conf  ev_ok  purpose  evidence
  ev_ok = 1 when the evidence text the model quoted really is in the function (checked by this script).
Starts the model server when it is not running and stops it after (GPU gate: run hoggate / gpu_queue first).
"""
import io, re, sys, json
sys.path.insert(0, r"C:\Users\john\Documents\Tools\llm")
import localread  # noqa: E402

HEAD = re.compile(r"^// ==== (\S+) @ (\S+) body=(\d+)", re.M)
MAXCH = 24000
SYSTEM = ("You name functions of a decompiled ARM game binary (LittleBigPlanet PS Vita, in-game level editor code; "
          "the poppet is the editor menu / cursor tool). Reply with ONE JSON object only, no other text: "
          '{"name": "Prefix_VerbObject", "conf": 1-5, "purpose": "one short sentence", "evidence": "one line copied exactly from the code"}. '
          "Name = CamelCase with one of these prefixes: %s. Base the name only on what the code does "
          "(callee names, constants, fields); conf 1 = guess, 5 = certain.")


def split(text):
    """[(name, addr, body text)] of a DumpDecomp file"""
    ms = list(HEAD.finditer(text))
    return [(m.group(1), m.group(2), text[m.end():(ms[i + 1].start() if i + 1 < len(ms) else len(text))])
            for i, m in enumerate(ms)]


def blind(name, addr, body):
    body = re.sub(r"/\* Hand-named:.*?\*/\s*", "", body, flags=re.S)
    return body.replace(name, "FUN_" + addr)


def parse(reply):
    m = re.search(r"\{.*\}", reply, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    return d if isinstance(d, dict) else {}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def load_ctx(path):
    """addr -> (named callers, strings) from the funcinfo table"""
    names = {}; calls = {}; strs = {}; cur = None
    for l in io.open(path, encoding="utf-8", errors="replace"):
        f = l.rstrip(chr(10)).split(" ", 4)
        if f[0] == "F" and len(f) >= 5: cur = f[1]; names[cur] = (f[2], f[3]); calls[cur] = set(); strs[cur] = []
        elif f[0] == "C" and cur and len(f) == 2: calls[cur].add(f[1])
        elif f[0] == "S" and cur: strs[cur].append(l[2:].strip()[:60])
    callers = {}
    for a, cs in calls.items():
        if names[a][1] == "USER_DEFINED":
            for c in cs: callers.setdefault(c, []).append(names[a][0])
    return callers, strs


def extra(ctx, name, addr, hide):
    if not ctx: return ""
    word = name.split("_", 1)[-1]
    cl = [c for c in ctx[0].get(addr, []) if not (hide and word in c)][:12]
    st = list(dict.fromkeys(ctx[1].get(addr, [])))[:12]
    return "Named callers: %s%sStrings used: %s%s" % (", ".join(cl) or "none", chr(10), " | ".join(st) or "none", chr(10))


def one(port, system, name, addr, body, hide, ctx=None):
    code = blind(name, addr, body) if hide else body
    d = parse(localread.ask(port, system, "%sFunction at %s:%s%s" % (extra(ctx, name, addr, hide), addr, chr(10), code[:MAXCH]), 300))
    ev = norm(str(d.get("evidence", "")))
    ok = int(len(ev) >= 6 and ev.rstrip(";") in norm(code))
    prop = re.sub(r"[^A-Za-z0-9_]", "", str(d.get("name", "")))
    return [addr, name, prop or "-", str(d.get("conf", "-")), str(ok), norm(str(d.get("purpose", "-"))), ev or "-"]


def opt(args, key, default=None):
    return args[args.index(key) + 1] if key in args else default


def main():
    args = sys.argv[1:]
    hide = "--blind" in args
    pref = opt(args, "--prefixes", "Poppet_,Undo_,Joint_,Msg_On,Game_,Thing_,World_")
    ctx = load_ctx(opt(args, "--ctx")) if "--ctx" in args else None
    system = SYSTEM % pref
    if "--glossary" in args: system += chr(10) + io.open(opt(args, "--glossary"), encoding="utf-8").read()
    funcs = split(io.open(args[0], encoding="utf-8", errors="replace").read())
    own, port = localread.open_server("sage")
    try:
        with io.open(args[1], "w", encoding="utf-8", newline="\n") as o:
            o.write("\t".join("addr current proposed conf ev_ok purpose evidence".split()) + "\n")
            for i, (name, addr, body) in enumerate(funcs):
                row = one(port, system, name, addr, body, hide, ctx)
                o.write("\t".join(row) + "\n"); o.flush()
                print("%d/%d %s -> %s" % (i + 1, len(funcs), name, row[2]), flush=True)
    finally:
        if own: own.kill()


main()
