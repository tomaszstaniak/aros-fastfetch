# aros-x86_64-abiv11-pc (AROS-dev docs/coding-standards.md, "Target names").
set(CMAKE_SYSTEM_PROCESSOR x86_64)
include("${CMAKE_CURRENT_LIST_DIR}/aros-common.cmake")
# ABIv11 passes the library base in r12, set by inline asm around each
# library call, and its GCC 10.5 keeps r12 out of register allocation
# (FIXED_REGISTERS in tools/crosstools/gnu/gcc-10.5.0-aros.diff). The GCC 13
# used here for C23 does not, and reused r12 between the asm that loads the
# base and the call: OpenDevice ran with a wrong base and crashed
# ("Privilege violation", pool v11-1, 2026-10-27).
set(CMAKE_C_FLAGS_INIT "${AROS_C_FLAGS_INIT} -ffixed-r12")
