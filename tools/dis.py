# dis.py <eboot.elf> <start> <end> : Thumb-2 disassembly; va -> file offset = va - 0x81000000 + 0x80
import sys, struct, capstone
f = open(sys.argv[1], "rb").read()
a, b = int(sys.argv[2], 16), int(sys.argv[3], 16)
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
md.skipdata = True
for i in md.disasm(f[a - 0x81000000 + 0x80:b - 0x81000000 + 0x80], a):
    s = i.op_str
    if i.mnemonic.startswith("vldr") and "[pc" in s:
        off = int(s.split("#")[1].rstrip("]"), 16)
        t = ((i.address + 4) & ~3) + off
        v = struct.unpack_from("<f", f, t - 0x81000000 + 0x80)[0]
        s += "   ; =%g" % v
    print("%08x %-8s %s" % (i.address, i.mnemonic, s))
