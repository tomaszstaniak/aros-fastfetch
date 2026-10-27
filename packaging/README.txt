Fastfetch @VERSION@ for AROS
Build: @TARGET@ (@SYSTEM@)

Fastfetch shows information about the system next to the AROS logo:
AROS version and ABI, kernel (exec.library), uptime, screen mode,
Wanderer and Intuition versions, terminal, processor, memory, volumes,
local IP address and locale. In Limpet it can show the AROS logo as a
picture.

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
    fastfetch                    the compact view: small logo, the details
    fastfetch -c aros-logo       the AROS logo as a picture (Limpet 0.8.0
                                 or later), details in groups with bars
    fastfetch --help             all options
    fastfetch --format json      the same data as JSON
    fastfetch -c neofetch        a preset from share/fastfetch/presets
    fastfetch --logo none        no logo
    fastfetch --dynamic-interval 1000
                                 refresh every second until Ctrl-C

A terminal that reports its capabilities (Limpet 0.8.0 or later) gets
colours, its name and version, UTF-8 text and pictures. The standard
Shell window (CON:) gets plain text in the character set chosen in
Locale preferences. Long lines are cut at the window's edge. Output redirected to a file, and
JSON, contain no escape sequences; there, and in CON:,
--dynamic-interval prints each round after the last.

Configuration
-------------
    fastfetch --gen-config       writes ENVARC:fastfetch/config.jsonc

Fastfetch reads ENVARC:fastfetch/config.jsonc, then ENV:fastfetch/, then
share/fastfetch/config.jsonc in the drawer it was started from, which is
the compact view; copy that file to ENVARC:fastfetch/ to change it. The file format is that of Fastfetch on
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
The AROS logo in share/fastfetch/logos/aros.png comes from the AROS
source tree (images/AROS_600x300.png) under the AROS Public License 1.1
(Licenses/aros-logo-APL-1.1.txt).
Source/ holds the patches applied to Fastfetch for AROS and the exact
upstream version they apply to.

Original program: https://github.com/fastfetch-cli/fastfetch
