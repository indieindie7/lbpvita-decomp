// Pre-analysis seeding for a PS Vita ELF (no symbols): Thumb mode for the code range, ARM import stubs named from
// names_imports.txt (16-byte stubs), Thumb entry points from odd pointers found in the image, module exports.
// args: <names_imports.txt> <codeStart> <stubStart> <stubEnd>
//@category Vita
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.SourceType;
import java.math.BigInteger;
import java.nio.file.*;

public class SeedVita extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        long cs = Long.decode(a[1]), ss = Long.decode(a[2]), se = Long.decode(a[3]);
        Register tm = currentProgram.getRegister("TMode");
        ProgramContext pc = currentProgram.getProgramContext();
        pc.setValue(tm, toAddr(cs), toAddr(ss - 1), BigInteger.ONE);
        pc.setValue(tm, toAddr(ss), toAddr(se - 1), BigInteger.ZERO);
        int imp = 0, ptr = 0;
        for (String line : Files.readAllLines(Paths.get(a[0]))) {
            String[] t = line.trim().split(" ");
            if (t.length < 5) continue;
            Address ad = toAddr(Long.decode(t[0]));
            if (t[1].equals("func")) {
                disassemble(ad);
                Function f = getFunctionAt(ad);
                if (f == null) f = createFunction(ad, t[2]);
                if (f != null) { f.setName(t[2], SourceType.IMPORTED); setPlateComment(ad, "Vita import " + t[4] + " (vitasdk NID db)"); imp++; }
            } else createLabel(ad, t[2], true, SourceType.IMPORTED);
        }
        Memory mem = currentProgram.getMemory();
        java.util.TreeSet<Long> seeds = new java.util.TreeSet<>();
        for (MemoryBlock b : mem.getBlocks()) {
            println("block " + b.getName() + " " + b.getStart() + " " + b.getEnd() + " init=" + b.isInitialized());
            if (!b.isInitialized() || b.getStart().getAddressSpace() != currentProgram.getAddressFactory().getDefaultAddressSpace() || b.getSize() > 0x4000000L) continue;
            long s = b.getStart().getOffset(), e = b.getEnd().getOffset();
            long from = (s < ss) ? Math.max(s, se) : s;   // skip the code itself (literal pools get found by analysis)
            from = (from + 3) & ~3L;
            if (e < from + 4) continue;
            byte[] buf = new byte[(int) (e - from + 1)];
            mem.getBytes(toAddr(from), buf);
            for (int i = 0; i + 4 <= buf.length; i += 4) {
                long v = (buf[i] & 0xffL) | (buf[i + 1] & 0xffL) << 8 | (buf[i + 2] & 0xffL) << 16 | (buf[i + 3] & 0xffL) << 24;
                if ((v & 1) == 1 && v >= cs && v < ss) seeds.add(v - 1);
            }
        }
        for (long v : seeds) {
            Address ad = toAddr(v);
            if (getInstructionContaining(ad) == null) disassemble(ad);
            if (getInstructionAt(ad) != null && getFunctionAt(ad) == null && createFunction(ad, null) != null) ptr++;
            if (monitor.isCancelled()) break;
        }
        for (int i = 4; i < a.length; i++) {   // extra Thumb entries outside the main code range
            Address ad = toAddr(Long.decode(a[i]));
            pc.setValue(tm, ad, ad.add(0x3f), BigInteger.ONE);
            disassemble(ad); createFunction(ad, null);
        }
        println("SeedVita: imports " + imp + ", pointer seeds " + seeds.size() + ", functions created " + ptr);
    }
}
