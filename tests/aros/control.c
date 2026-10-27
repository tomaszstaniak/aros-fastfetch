/* Memory control for smoke.script's repeated runs: a C program that opens
 * the same C library and does nothing but print one line. What the system
 * keeps per run of this (mainline posixc keeps about 164 KB per open) is
 * not fastfetch's. Build it with the target's own toolchain and SDK. */
#include <stdio.h>

int main(void)
{
    printf("control\n");
    return 0;
}
