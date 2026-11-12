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
- `AROS_INCLUDE_AFTER` (optional): headers of the same system that its SDK
  does not ship, searched after the SDK's (`-idirafter`). The ABIv11
  2026.09 SDK lacks the OOP, HIDD and PCI headers the GPU module needs;
  `gen/include` of an ABIv11 build tree provides them.

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

`tests/aros/r2.script`, after it, covers the checks added in 2.70.0-r2:
configuration paths, CPU cores and the default route as JSON, the Command
module with a program in a drawer with spaces and three commands at once,
the picture logo with output to a file, and a Polish volume name under
ISO-8859-2 (it renames RAM: and sets ENV:CHARSET for those runs and puts
both back; with ENV:CHARSET already set it skips that part):

```
Execute r2.script BIN=<drawer>/fastfetch OUT=<results drawer> CMD=<drawer>/r2-command.jsonc
```

`tests/aros/r3.script` covers 2.70.0-r3: which configuration is read (a
file in ENV: and a different one in ENVARC:, then neither), `--gen-config`,
groups left out with `--structure-disabled`, JSON of the picture preset and
a huge `--logo-width`. It skips the order checks when either file is
already there:

```
Execute r3.script BIN=<drawer>/fastfetch OUT=<results drawer> DIR=<drawer with r3-kept.jsonc and r3-session.jsonc>
```

`tests/aros/gpu.script` covers the GPU module of 2.70.0-r4: text, JSON
and the module's format with the temperature off and on, the other
modules beside it, repeated runs, rounds with `--dynamic-interval` ended
with Break C, and the system versions. Module options are in
`gpu-temp.jsonc` and `gpu-format.jsonc`: Fastfetch 2.70 takes none on the
command line. With `PROBE=`, it first runs
`tests/aros/gpuprobe.c`, which prints what pci.hidd, the graphics drivers,
their relations and telemetry answer, unprocessed, so that every value
Fastfetch shows can be traced:

```
Execute gpu.script BIN=<drawer>/fastfetch OUT=<results drawer> DIR=<drawer with gpu-temp.jsonc and gpu-format.jsonc> PROBE=<drawer>/gpuprobe
```

Build the probe with the target's SDK toolchain, for example
`x86_64-aros-gcc --sysroot=<SDK> -O2 -Wall tests/aros/gpuprobe.c -o gpuprobe`
(with `-idirafter <AROS_INCLUDE_AFTER>` for ABIv11).

### Checking the GPU module on a physical card

QEMU shows a PCI display controller without a driver relation or sensors,
so driver, memory and temperature are only exercised on real hardware.
On mainline AROS with hiddclass 1.3 (nightly 20261110 or later), with a
card that a relating driver runs (nvgfx for NVIDIA; amdgpu, radeon,
nvidia and vmwaresvga relate the device but measure no memory):

1. Run `gpu.script` with `PROBE=` as above and keep the results drawer.
2. In `gpu-probe.txt`, the card's `PCI` line must list a relation of type
   `0x00000002` (its driver) to a `hidd.gfx.*` class. For nvgfx, the
   driver's `MemoryAttribs` must give four numbers, and relations of type
   `0x80000007` (sensors monitoring the card) must include a
   `hidd.telemetry.thermal` object with its entries and its current
   reading.
3. Compare with `gpu-temp.json`: `name` is the pci.ids name of the card's
   vendor:device; `driver` is the driver's `name`; for nvgfx
   `memory.dedicated.total` is the first MemoryAttribs number and `used`
   the first minus the second, `shared` the same for the third and
   fourth; `temperature` is the thermal zone's current reading divided by
   1000, not its `Critical` or `Passive` entry. In `gpu.json` (temperature
   off) `temperature` is null.
4. Other drivers: `driver` set, memory null. With two cards, two results
   with different `deviceId`.
5. Remove the card's driver from DEVS:Monitors (or boot without it): the
   card stays listed by name, with an empty driver.

Console output (CON:, Limpet: the compact view, the picture logo, a narrow
window through Limpet's `win-inject`), Ctrl-C and timing are checked by
hand.

The vendored Limpet SDK must include `limpet_query_geometry` and
`limpet_has_kitty_graphics` (Limpet main eae72f2 and later).
