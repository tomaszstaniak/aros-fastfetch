// Host harness for src/detection/gpu/gpu_aros_values.c (tests/test_port.py).
//   temp UNIT VALUE             degrees Celsius or "unknown"
//   mem HAVETOTAL TOTAL HAVEFREE FREE
//                               "TOTAL USED", each a number or "unknown"
//   path STRING                 "S B D F" or "invalid"
//   memdriver CLASS...          "yes" or "no"
//   select                      stdin lines "OBJECT FUNCTION SUBCLASS",
//                               prints the kept objects in order
#include "detection/gpu/gpu_aros_values.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void printValue(uint64_t v) {
    if (v == FF_AROS_GPU_MEM_UNKNOWN) {
        fputs("unknown", stdout);
    } else {
        printf("%" PRIu64, v);
    }
}

int main(int argc, char** argv) {
    if (argc < 2) {
        return 2;
    }
    if (strcmp(argv[1], "temp") == 0 && argc == 4) {
        double t = ffArosGpuTemperature((uint32_t) strtoul(argv[2], NULL, 0), (int32_t) strtol(argv[3], NULL, 0));
        if (t == FF_AROS_GPU_TEMP_UNKNOWN) {
            puts("unknown");
        } else {
            printf("%.3f\n", t);
        }
        return 0;
    }
    if (strcmp(argv[1], "mem") == 0 && argc == 6) {
        FFArosGpuMemory m = ffArosGpuMemory(atoi(argv[2]) != 0, strtoull(argv[3], NULL, 0),
            atoi(argv[4]) != 0, strtoull(argv[5], NULL, 0));
        printValue(m.total);
        putchar(' ');
        printValue(m.used);
        putchar('\n');
        return 0;
    }
    if (strcmp(argv[1], "path") == 0 && argc == 3) {
        uint32_t s = 99, b = 99, d = 99, f = 99;
        if (ffArosGpuParsePciPath(strcmp(argv[2], "NULL") == 0 ? NULL : argv[2], &s, &b, &d, &f)) {
            printf("%u %u %u %u\n", s, b, d, f);
        } else {
            printf("invalid %u %u %u %u\n", s, b, d, f);
        }
        return 0;
    }
    if (strcmp(argv[1], "memdriver") == 0) {
        puts(ffArosGpuDriverReportsMemory((const char* const*) argv + 2, (uint32_t) (argc - 2)) ? "yes" : "no");
        return 0;
    }
    if (strcmp(argv[1], "select") == 0) {
        FFArosGpuPciEntry entries[32];
        uint32_t count = 0;
        unsigned long object;
        unsigned function, subclass;
        while (count < 32 && scanf("%lu %u %u", &object, &function, &subclass) == 3) {
            entries[count++] = (FFArosGpuPciEntry) {
                .object = (const void*) (uintptr_t) object,
                .function = function,
                .subclass = (uint8_t) subclass,
            };
        }
        uint32_t kept = ffArosGpuSelectPci(entries, count);
        for (uint32_t i = 0; i < kept; i++) {
            printf("%lu\n", (unsigned long) (uintptr_t) entries[i].object);
        }
        return 0;
    }
    return 2;
}
