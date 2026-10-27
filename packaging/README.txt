Fastfetch @VERSION@ for AROS
Build: @TARGET@ (@SYSTEM@)

Fastfetch shows information about the system next to the AROS logo:
AROS version and ABI, kernel (exec.library), uptime, screen mode,
Wanderer and Intuition versions, fonts, terminal, processor, memory,
volumes, local IP address and locale.

Installation
------------
Unpack the archive into any drawer, for example Work:, and add the
Fastfetch drawer to the Shell's search path, e.g. in S:User-Startup:

    Path Work:Fastfetch ADD

Then type fastfetch in a Shell. The archive is also an apkg package: once
an apkg catalogue lists it, "apkg install fastfetch" installs it and
"apkg run fastfetch" starts it.

Use
---
    fastfetch                    the logo and the system information
    fastfetch --help             all options
    fastfetch --format json      the same data as JSON
    fastfetch -c neofetch        a preset from share/fastfetch/presets
    fastfetch --logo none        no logo
    fastfetch --dynamic-interval 1000
                                 refresh every second until Ctrl-C

A terminal that reports its capabilities (Limpet 0.8.0 or later) gets
colours, its name and version, and UTF-8 text. The standard Shell window
(CON:) gets plain text in ISO-8859-1. Output redirected to a file, and
JSON, contain no escape sequences (--dynamic-interval redraws the screen
and is meant for a console).

Configuration
-------------
    fastfetch --gen-config       writes ENVARC:fastfetch/config.jsonc

Fastfetch reads ENVARC:fastfetch/config.jsonc, then ENV:fastfetch/, then
the drawer it was started from. The file format is that of Fastfetch on
other systems: https://github.com/fastfetch-cli/fastfetch/wiki/Configuration
Paths in it are AmigaDOS paths.

Limitations
-----------
- The Shell's version is not shown: it is part of the system and has no
  version string to read.
- GPU, sound, battery, swap, theme, packages, DNS and user modules report
  that they are not supported on AROS.
- Local IP needs a running TCP/IP stack (AROSTCP); without one the module
  says so and the rest of the output is unchanged.
- The disk sizes are those the file system reports for each mounted volume.
@PI@

Licences
--------
Fastfetch is MIT-licensed (LICENSE.txt). It includes yyjson (MIT),
widecharwidth (public domain) and the Limpet SDK (MIT); see Licenses/.
Source/ holds the patches applied to Fastfetch for AROS and the exact
upstream version they apply to.

Original program: https://github.com/fastfetch-cli/fastfetch
