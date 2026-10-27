# Fastfetch for AROS

[Fastfetch](https://github.com/fastfetch-cli/fastfetch) 2.70.0 for AROS: it
shows the AROS logo next to information about the running system (AROS
version and ABI, kernel, uptime, screen mode, Wanderer and Intuition, fonts,
terminal, processor, memory, volumes, local IP address, locale). The data
comes from AROS itself (exec, dos, graphics, intuition, locale,
processor.resource, bsdsocket.library); nothing is taken from Linux files.

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

`fastfetch --gen-config` writes `ENVARC:fastfetch/config.jsonc`. Fastfetch
reads `ENVARC:fastfetch/`, then `ENV:fastfetch/`, then its own drawer.
Presets are in `share/fastfetch/presets` in the drawer.

Colours, the terminal's name and UTF-8 text depend on what the console
reports through the Limpet capabilities contract on the actual output
(Limpet 0.8.0 and later report all of them). The standard Shell window
(CON:) gets plain ISO-8859-1 text. Redirected output and JSON contain no
escape sequences, except with `--dynamic-interval`, which redraws the
screen in place by definition.

Modules without a reliable source on AROS (GPU, sound, battery, swap,
themes, packages, DNS, users) report that they are not supported; the
default output leaves them out. Local IP needs a running TCP/IP stack.

## Building

See [development](docs/development.md) and the [patch workflow](docs/patching.md).
Fastfetch and the included yyjson and Limpet SDK are MIT-licensed; the
packages carry their licences and the patch series.
