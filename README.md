# LittleBigPlanet PS Vita (PCSF00021 v01.00) reverse-engineering names

Function names for the main module of **LittleBigPlanet PlayStation Vita** (Tarsier / Double Eleven / XDev, 2012), EU release PCSF00021 v01.00. Module name in the binary: `LBP2_Final`.
One search (2026-11-14) found no public decomp of the Vita or PSP game. This is a first pass: every function has a name (0 `FUN_` left), but **all names except the SDK imports are provisional and mostly structural**.

| | |
|---|---|
| Image | `eboot.bin` fself (12,354,320 B) -> ELF 12,350,224 B, ARMv7 Thumb-2, e_type 0xFE00 |
| Segments | RX 0x81000000 size 0x85FB54; RW 0x81860000 size 0x367290 |
| Code | 0x81000000..0x81763E38 (function bodies cover 97.5 %), import stubs 0x81763E38..0x81766468 |
| Functions | 30,095 |
| SDK imports (NID -> name, vitasdk/vita-headers `c00157c`) | 611 stubs, 48 libraries; 600 of 619 NIDs (functions + variables) resolved, the rest are `<Lib>_<NID>` |
| hand | 2,765 lines in `ghidra/hand.txt`: `module_start`, 2,737 script-native functions named from the game script-native table (`tools/natives.py`), 27 Poppet (create mode) functions named by reading the code |
| `str`: named from a string the function references | 1,967 |
| `src`: references only a source-path string (`<file>_fn_<addr>`) | 374 |
| `imp`: named after the rarest SDK import it calls (`<area>_use_<import>_<addr>`) | 2,763 |
| `rule`: structural (`<area>_<Role>_<addr>`; role from size and callee count) | 24,381 |

`<area>` is the stem of the nearest function that references a `.cpp` build path (e.g. `fmod_codec_it`), `fmod` between two FMOD anchors, otherwise `lbp`. It is an address-proximity guess, not a fact.
Roles: `Stub` (<= 4 B), `LeafS/M/L` (no calls), `Thunk`/`Wrap` (one callee), `Proc` (2-9 callees), `Run` (10+).
Not done: C++ class recovery (vtables), the bundled libraries (FMOD, libpng and others are only labelled by strings), `libult.suprx` / `steroid.suprx`, data labels.

**No game data is included**: no VPK, eboot, ELF or decompiled C. `funcinfo.tsv` holds only function addresses, names, sizes and call edges.

## Layout
| Path | Content |
|---|---|
| `ghidra/names_imports.txt` | import stub address -> SDK name |
| `ghidra/names_auto.txt` | `0x<addr> func <name> <tag> <note>` for all provisional names |
| `ghidra/hand.txt` | hand names (applied last) |
| `LEVELEDIT.md` | how the create-mode tools work: state stack, messages, undo, vertex edit, slice, glue, flood fill |
| `enums.txt` | 138 reflection enum tables (2,961 entries) read from the binary by `tools/enums.py` |
| `tools/natives.py`, `enums.py`, `strs.py`, `ptrs.py`, `vtab.py` | script-native table, enum tables, string search, pointer sites, vtable listing |
| `ghidra/dump.sh` + `scripts/DumpRange.java` | decompile an address range to a local file (output is never committed) |
| `ghidra/funcinfo.tsv` | `F` address name source size, `C` callee |
| `ghidra/scripts/` | SeedVita (Thumb context, import stubs, pointer seeds), ApplyNames, ExportFuncInfo |
| `tools/` | fself.py / unfself.py (fself -> ELF), modinfo.py (module info, imports), nids.py (NID db lookup), autoname.py, stats.py |

## Reproduce
1. From your own dump: unzip `eboot.bin` from the VPK (it must be a decrypted fself). `tools/unfself.py eboot.bin bin/eboot.elf`.
2. `tools/modinfo.py bin/eboot.elf imports_raw.tsv`; clone vitasdk/vita-headers; `tools/nids.py <vita-headers> imports_raw.tsv names_imports.txt`.
3. `ghidra/import.sh` (Ghidra 12.1, `ARM:LE:32:v8T`; adjust paths), then `tools/autoname.py work/funcinfo.tsv work/auto.txt` and `ghidra/apply.sh`.

Non-commercial study and preservation. Notes, names and tools: MIT (`LICENSE`). LittleBigPlanet belongs to its rights holders.
