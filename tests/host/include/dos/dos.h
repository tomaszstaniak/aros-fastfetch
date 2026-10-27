/* Just enough of dos/dos.h for the Limpet SDK header on the host: the output
   filter test needs its types, never a dos.library call. */
#ifndef DOS_DOS_H
#define DOS_DOS_H
#include <stdint.h>
typedef int32_t LONG;
typedef uint32_t ULONG;
typedef intptr_t BPTR;
typedef intptr_t SIPTR;
#define DOSTRUE (-1)
#define DOSFALSE 0
#define ERROR_ACTION_NOT_KNOWN 209
#endif
