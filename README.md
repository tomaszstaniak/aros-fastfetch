# Fastfetch for AROS

[Fastfetch](https://github.com/fastfetch-cli/fastfetch) 2.70.0 for AROS: it
shows the AROS logo next to information about the running system (AROS
version and ABI, kernel, uptime, screen mode, Wanderer and Intuition, fonts,
terminal, processor, memory, volumes, local IP address, locale). In Limpet it
can show the AROS logo as a picture. The data
comes from AROS itself (exec, dos, graphics, intuition, locale,
processor.resource, bsdsocket.library); nothing is taken from Linux files.

## Download

[Fastfetch 2.70.0-r6 for AROS](https://github.com/tomaszstaniak/aros-fastfetch/releases/tag/v2.70.0-r6)
is available for the three targets below, or with
[apkg](https://github.com/tomaszstaniak/arospkg): `apkg install fastfetch`.
The mainline and Raspberry Pi archives need a nightly build of 2026-11-24
or later; on earlier nightlies use
[revision 4](https://github.com/tomaszstaniak/aros-fastfetch/releases/tag/v2.70.0-r4).

In Limpet 0.14.0 or later, TAB completes the options and their values
(`fastfetch --logo-t`, TAB: `--logo-type`). The package brings the list in
`Completions/fastfetch`.

## Builds

| Archive target | System |
|---|---|
| `aros-x86_64-abiv11-pc` | AROS One and other ABIv11 systems on PC |
| `aros-x86_64-abiv1-pc` | mainline AROS (ABIv1) on PC |
| `aros-aarch64-abiv1-raspi` | native AROS on the Raspberry Pi |

A build runs only on its own ABI. The Raspberry Pi build is for the native
Pi system, not for every AArch64 AROS.

## Use

Unpack the archive, add its drawer to the Shell's path
(`Path Work:Fastfetch ADD`) and type `fastfetch`. The options are those of
Fastfetch on other systems: `fastfetch --help`, `--format json`,
`-c <preset>`, `--logo none`, `--dynamic-interval <ms>` (ends with Ctrl-C).

Without options it shows the compact view, the preset `aros-compact`: the
small logo, above the list when the window is too narrow for it beside (in
terminals that report their width), and lines cut at the window's edge
instead of wrapped. `fastfetch -c aros-logo` shows the AROS logo as a
picture with the details in groups and bars, in terminals that confirm Kitty
graphics (Limpet 0.8.0 and later), and the small text logo elsewhere;
`--logo FILE` takes any picture a datatype of the system reads. Both presets
name their groups of lines (`system`, `hardware`, `memory-disks`,
`network`), and `--structure-disabled network:hardware` leaves groups out.

Fastfetch reads `ENV:fastfetch/config.jsonc` (this session's copy), then
`ENVARC:fastfetch/config.jsonc` (kept over a restart), then the
`aros-compact` preset. `fastfetch --gen-config` writes
`ENVARC:fastfetch/config.jsonc`. Presets are in `share/fastfetch/presets`
in the drawer.

Colours, the terminal's name and UTF-8 text depend on what the console
reports through the Limpet capabilities contract on the actual output
(Limpet 0.8.0 and later report all of them). The standard Shell window
(CON:) gets plain text in the character set chosen in Locale preferences
(codesets.library's system set); names the system keeps are read in that set. Redirected output and JSON contain no
escape sequences; there, and in CON:, `--dynamic-interval` prints each
round after the last instead of redrawing the screen.

The GPU module lists the PCI display controllers, named from
`DEVS:pci.ids`. Where the graphics driver and its sensors are related to
the card through HIDD object relations (AROS mainline from November 2026),
it adds the driver's name, the card's memory from drivers that measure it
(nvgfx) and, with `"temp": true` in the GPU module's configuration, the
card's temperature. Firmware framebuffers (VESA, EFI, the Raspberry Pi's)
do not name a GPU and are not listed. Modules without a reliable source on AROS (sound, battery, swap,
themes, packages, DNS, users) report that they are not supported; the
default output leaves them and the GPU out. Local IP needs a running TCP/IP stack; the
default route is read from AROSTCP's routing table. Physical cores and
processor packages are not reported by AROS and are left unknown.

## Building

See [development](docs/development.md) and the [patch workflow](docs/patching.md).
Fastfetch and the included yyjson and Limpet SDK are MIT-licensed; the
packages carry their licences and the patch series. The AROS logo picture
(`packaging/logos/aros.png`) is the AROS tree's `images/AROS_600x300.png`
under the AROS Public License 1.1 ([its record](packaging/logos/README.md)).
