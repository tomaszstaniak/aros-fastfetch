# Development

Fastfetch is a C/CMake project and needs C23. The port builds it with
CMake 3.21 or later and one toolchain file per target in `cmake/`.

## Toolchains

Copy `local.example.json` to `local.json` (ignored) and fill in, per target:

- `AROS_CC`: a C compiler with C23. For x86_64 this is GCC 13 for AROS; the
  SDK's GCC 10.5 lacks C23.
- `AROS_LINK_CC`: the GCC driver of the toolchain built with that SDK. It
  links: startup code, libgcc and collect-aros must match the SDK.
- `AROS_SDK`: the target's SDK (Developer drawer).
- `AROS_AR`: an archiver.

and `apkg_pack`: arospkg's `tools/apkg-pack`, used to write the PC archives.

ABIv11 passes a library's base in r12, set by inline assembly around each
library call; its GCC 10.5 keeps r12 out of register allocation, GCC 13 does
not. `cmake/aros-x86_64-abiv11-pc.cmake` therefore compiles with
`-ffixed-r12`. Without it, library calls receive a wrong base and the
program crashes ("Privilege violation").

The Raspberry Pi target uses the Pi SDK's Clang 20 for compiling and linking.

## Commands

```sh
scripts/fastfetch.py materialize          # work/fastfetch from the pin and the series
scripts/fastfetch.py verify               # the series reproduces work/fastfetch
scripts/fastfetch.py build TARGET         # build/TARGET from a fresh reconstruction
scripts/fastfetch.py package TARGET VER   # dist/Fastfetch-VER-TARGET.zip, VER e.g. 2.70.0-r1
scripts/fastfetch.py test                 # host tests
```

`build` refuses an existing `build/TARGET`; `package` refuses an existing
archive and appends to `dist/SHA256SUMS`. `build --from-work` builds the
work tree instead, for development.

The Limpet SDK sources (presentation and identity queries) are vendored in
`vendor/limpet-sdk` with their checksums; the README there names the Limpet
commit they come from.

## Guest checks

`tests/aros/smoke.script` runs one build through the redirected checks
(version, help, default output, JSON, unsupported modules, configuration,
fifteen repeated runs with memory and process list) and writes each result
to its own file:

```
Execute smoke.script BIN=<drawer>/fastfetch CFG=<drawer>/custom.jsonc OUT=<new results drawer>
```

Console output (CON:, Limpet), Ctrl-C and timing are checked by hand.
