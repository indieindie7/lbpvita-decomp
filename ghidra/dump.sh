#!/bin/bash
# dump.sh <name> <start> <end> : decompile a range to work/decomp_<name>.c (read-only)
cd "$(dirname "$0")"
W=$(cygpath -w "$PWD"); export GHIDRA_HEADLESS_MAXMEM=12G
cmd //c "..\..\Tools\ghidra-headless.bat" "$W" LBPV -process eboot.elf -noanalysis -readOnly -scriptPath "$W\scripts" -postScript DumpRange.java "$W\work\decomp_$1.c" $2 $3 > work/dump_$1.log 2>&1
grep 'DumpRange:\|ERROR' work/dump_$1.log | cut -c1-200 | head -5; ls -la work/decomp_$1.c
