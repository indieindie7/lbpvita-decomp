#!/bin/bash
# Import eboot.elf, seed, analyse. One headless job at a time.
cd "$(dirname "$0")"
rm -rf LBPV.rep LBPV.gpr LBPV.lock*
export GHIDRA_HEADLESS_MAXMEM=12G
W=$(cygpath -w "$PWD")
cmd //c "..\..\Tools\ghidra-headless.bat" "$W" LBPV -import "$W\..\bin\eboot.elf" -processor ARM:LE:32:v8T -cspec default -scriptPath "$W\scripts" -preScript SeedVita.java "$W\..\names_imports.txt" 0x81000000 0x81763e38 0x81766468 0x8185fb14 -postScript ExportFuncInfo.java "$W\work\funcinfo.tsv" -analysisTimeoutPerFile 7200 > work/import.log 2>&1
tail -5 work/import.log
