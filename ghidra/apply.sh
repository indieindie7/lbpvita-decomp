#!/bin/bash
# apply.sh : names (auto then hand) -> project, export funcinfo. One headless job at a time.
cd "$(dirname "$0")"
W=$(cygpath -w "$PWD"); export GHIDRA_HEADLESS_MAXMEM=12G
cmd //c "..\..\Tools\ghidra-headless.bat" "$W" LBPV -process eboot.elf -noanalysis -scriptPath "$W\scripts" -postScript ApplyNames.java "$W\work\auto.txt" -postScript ApplyNames.java "$W\work\hand.txt" -postScript ExportFuncInfo.java "$W\work\funcinfo_named.tsv" > work/apply.log 2>&1
grep 'ApplyNames:\|ExportFuncInfo:\|ERROR' work/apply.log | cut -c1-200 | head
