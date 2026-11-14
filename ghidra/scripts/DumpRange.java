// Dump decompiled C for every function with entry in [start,end).  args: <out.c> <start> <end>   (local study only, never published)
//@category Vita
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;
public class DumpRange extends GhidraScript {
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter w = new PrintWriter(new FileWriter(a[0]));
        DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
        AddressSet set = new AddressSet(toAddr(Long.decode(a[1])), toAddr(Long.decode(a[2]) - 1));
        int n = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(set, true)) {
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            w.println("// ==== " + f.getName() + " @ " + f.getEntryPoint() + " size=" + f.getBody().getNumAddresses());
            if (r.decompileCompleted()) w.println(r.getDecompiledFunction().getC()); else w.println("// failed: " + r.getErrorMessage());
            n++;
        }
        di.dispose(); w.close(); println("DumpRange: done " + n);
    }
}
