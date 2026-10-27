# Shared part of the AROS cross toolchain files. Paths are cache variables,
# passed by scripts/fastfetch.py from local.json; nothing here is
# machine-specific.
#   AROS_CC       C compiler with C23 (Fastfetch requires it)
#   AROS_LINK_CC  driver that links: startup code, libgcc and collect-aros of
#                 the toolchain built with this SDK (may equal AROS_CC)
#   AROS_SDK      Developer SDK of the target system (sysroot)
#   AROS_AR       archiver
set(CMAKE_SYSTEM_NAME AROS)
set(CMAKE_SYSTEM_VERSION 1)
# CMake reads this file again in its own try-compile projects; pass the
# paths on to them.
list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES AROS_CC AROS_LINK_CC AROS_SDK AROS_AR)
foreach(var AROS_CC AROS_LINK_CC AROS_SDK AROS_AR)
    if(NOT ${var})
        message(FATAL_ERROR "${var} is not set: copy local.example.json to local.json and fill it in")
    endif()
endforeach()
set(CMAKE_C_COMPILER "${AROS_CC}")
set(CMAKE_AR "${AROS_AR}" CACHE FILEPATH "" FORCE)
set(CMAKE_SYSROOT "${AROS_SDK}")
set(CMAKE_FIND_ROOT_PATH "${AROS_SDK}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
# Try-compile links would need the AROS startup; a static library check
# is enough to see that the compiler works.
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
# AROS executables are relocatable ELF linked by collect-aros through the
# GCC driver of the SDK's own toolchain.
set(CMAKE_C_LINK_EXECUTABLE "${AROS_LINK_CC} --sysroot=${AROS_SDK} <FLAGS> <CMAKE_C_LINK_FLAGS> <LINK_FLAGS> <OBJECTS> -o <TARGET> <LINK_LIBRARIES>")
