# Development

Fastfetch is a C/CMake project. Upstream 2.70.0 requires CMake 3.21 or later.
AROS platform support must be implemented; selecting a Linux build is not a port.

Read upstreams.json for the exact source revision and docs/patching.md for the
source workflow. No AROS build command has been verified yet. Future scripts must
accept externally configured SDK/toolchain paths and use separate target builds.
Do not store SDKs, compilers or VM images here.

Before handoff, remove obsolete builds and redundant packages. Keep source
patches, final assets, checksums and compact reproduction records.
