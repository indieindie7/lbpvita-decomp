# vtscan.py <elf> <funcinfo.tsv> <out.tsv> : find vtables = runs of >=3 thumb pointers to function starts in data;
# writes: vtable va, slots, ref count (literal-pool refs in text), first referencing function, slot function names
import sys, struct, bisect
d = open(sys.argv[1], 'rb').read()
BASE, HDR, TEND = 0x81000000, 0x80, 0x81763e38
F = {}
for l in open(sys.argv[2], encoding='utf8', errors='replace'):
    if l.startswith('F '):
        t = l.split(); F[int(t[1], 16)] = t[2]
starts = sorted(F)
def owner(va):
    i = bisect.bisect_right(starts, va) - 1
    return starts[i] if i >= 0 else 0
n = (len(d) - HDR) // 4
words = struct.unpack_from('<%dI' % n, d, HDR)
tw = (TEND - BASE) // 4
lit = {}
for i in range(tw):
    w = words[i]
    if TEND <= w < BASE + n * 4 and not w & 3:
        lit.setdefault(w, []).append(BASE + 4 * i)
# movw/movt pairs (Thumb-2 T3 encodings) in text
hw = struct.unpack_from('<%dH' % (tw * 2), d, HDR)
pend = {}
def imm16(a, b): return ((a & 0xF) << 12) | (((a >> 10) & 1) << 11) | (((b >> 12) & 7) << 8) | (b & 0xFF)
k = 0
while k < tw * 2 - 1:
    a, b = hw[k], hw[k + 1]
    if a & 0xF800 in (0xE800, 0xF000, 0xF800):
        if not b & 0x8000:
            rd = (b >> 8) & 0xF
            if a & 0xFBF0 == 0xF240: pend[rd] = (imm16(a, b), k)
            elif a & 0xFBF0 == 0xF2C0 and rd in pend and k - pend[rd][1] <= 16:
                v = (imm16(a, b) << 16) | pend[rd][0]
                if TEND <= v < BASE + n * 4: lit.setdefault(v, []).append(BASE + 2 * k)
        k += 2
    else: k += 1
out = []; i = tw
while i < n:
    j = i
    while j < n and words[j] & 1 and BASE <= words[j] < TEND and (words[j] - 1) in F:
        j += 1
    if j - i >= 3:
        va = BASE + 4 * i
        refs = lit.get(va - 8, []) + lit.get(va, [])
        out.append((va, j - i, len(refs), ','.join(sorted(set(F.get(owner(r), '-') for r in refs))[:16]) if refs else '-', [F[words[k] - 1] for k in range(i, j)]))
    i = max(j, i + 1)
with open(sys.argv[3], 'w', encoding='utf8', newline='\n') as f:
    for va, c, r, o, s in out:
        f.write('%08x\t%d\t%d\t%s\t%s\n' % (va, c, r, o, ' '.join(s)))
print('vtables', len(out), 'with refs', sum(1 for x in out if x[2]), 'slots', sum(x[1] for x in out))
