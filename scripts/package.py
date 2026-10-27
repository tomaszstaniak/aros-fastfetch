#!/usr/bin/env python3
"""Assemble dist/Fastfetch-<VERSION>-<TARGET>.zip from build/<TARGET>.

    package.py TARGET VERSION BUILD_DIR

Called by `fastfetch.py package`, which has checked the executable against
its build record. The archive holds one drawer, Fastfetch/: the program,
its README and licences, the presets, and the patch series it was built
from. For the PC targets apkg-pack (arospkg) writes the archive with the
catalogue manifest in .arospkg/manifest.toml and checks it. The Raspberry Pi
archive has no manifest: the catalogue has no platform field, and an
aarch64/v1 entry would also be offered to Macaros (AROS-dev
docs/coding-standards.md, "Target names").

Archives in dist/ are never replaced; SHA256SUMS only gains lines.
"""
import hashlib, json, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "Fastfetch"
# Each target as the catalogue spells it, and the libraries the program
# opens that the system must provide (read from the binaries: the C
# library's own, which differ between the ABIs).
TARGETS = {
    "aros-x86_64-abiv11-pc": {"arch": "x86_64", "abi": "v11", "system": "AROS One and other ABIv11 systems on PC",
                              "requires": ["crt.library", "stdlib.library"]},
    "aros-x86_64-abiv1-pc": {"arch": "x86_64", "abi": "v1", "system": "mainline AROS (ABIv1) on PC",
                             "requires": ["posixc.library", "stdc.library", "stdcio.library"]},
    "aros-aarch64-abiv1-raspi": {"arch": "aarch64", "abi": "v1", "system": "native AROS on the Raspberry Pi (ABIv1)",
                                 "requires": None},
}
EPOCH = 315532800  # 1980-01-01, the ZIP format's first date: same bytes for the same files


def manifest(target, version, revision):
    t = TARGETS[target]
    lines = [
        'id              = "fastfetch"',
        f'version         = "{version}"',
        f"revision        = {revision}",
        'summary         = "System information in the Shell, with the AROS logo"',
        'category        = "utility/misc"',
        'license         = "MIT"',
        'kind            = "app"',
        f'arch            = "{t["arch"]}"',
        f'abi             = "{t["abi"]}"',
        f'subdir          = "{NAME}"',
        "depends         = []",
        "depends_checked = true",
        "",
    ]
    for lib in t["requires"]:
        lines += ["[[requires_system]]", 'type = "library"', f'id   = "{lib}"', ""]
    lines += ["[launch]", 'executable = "fastfetch"', 'mode       = "shell"', ""]
    return "\n".join(lines)


def readme(target, version):
    text = (ROOT / "packaging" / "README.txt").read_text()
    pi = ("- The processor's name is not shown: the system does not report it.\n"
          if target.endswith("-raspi") else "")
    return (text.replace("@VERSION@", version).replace("@TARGET@", target)
            .replace("@SYSTEM@", TARGETS[target]["system"]).replace("@PI@\n", pi))


def stage(drawer, target, version, build):
    src = build / "src"
    drawer.mkdir(parents=True)
    shutil.copy2(build / "cmake" / "fastfetch", drawer / "fastfetch")
    (drawer / "fastfetch").chmod(0o755)
    (drawer / "README.txt").write_text(readme(target, version))
    shutil.copy2(src / "LICENSE", drawer / "LICENSE.txt")
    lic = drawer / "Licenses"
    lic.mkdir()
    header = (src / "src" / "3rdparty" / "yyjson" / "yyjson.h").read_text()
    (lic / "yyjson.txt").write_text(header[:header.index("*/") + 2] + "\n")  # its MIT notice
    (lic / "widecharwidth.txt").write_text(
        "src/3rdparty/widecharwidth (https://github.com/ridiculousfish/widecharwidth),\n"
        "used for character widths, is in the public domain.\n")
    shutil.copy2(ROOT / "vendor" / "limpet-sdk" / "LICENSE.txt", lic / "limpet-sdk.txt")
    # Presets for -c NAME: fastfetch looks for fastfetch/presets/ in its data
    # directory, which is PROGDIR:share on AROS.
    shutil.copytree(src / "presets", drawer / "share" / "fastfetch" / "presets")
    packaging = ROOT / "packaging"
    for p in sorted((packaging / "presets").iterdir()):
        shutil.copy2(p, drawer / "share" / "fastfetch" / "presets" / p.name)
    # The compact view: PROGDIR: is the last configuration directory, so a
    # config of the user's own in ENVARC: or ENV: takes its place.
    (drawer / "fastfetch").mkdir()
    shutil.copy2(packaging / "fastfetch" / "config.jsonc", drawer / "fastfetch" / "config.jsonc")
    # The AROS logo for -c aros-logo, with its licence (packaging/logos/README.md).
    (drawer / "share" / "fastfetch" / "logos").mkdir()
    shutil.copy2(packaging / "logos" / "aros.png", drawer / "share" / "fastfetch" / "logos" / "aros.png")
    shutil.copy2(packaging / "logos" / "APL-1.1.txt", lic / "aros-logo-APL-1.1.txt")
    source = drawer / "Source"
    (source / "patches").mkdir(parents=True)
    shutil.copy2(ROOT / "upstreams.json", source / "upstreams.json")
    for p in sorted((ROOT / "patches" / "fastfetch").iterdir()):
        shutil.copy2(p, source / "patches" / p.name)
    record = json.loads((build / "build-record.json").read_text())
    (source / "BUILD.json").write_text(json.dumps(record, indent=2) + "\n")


def write_zip(drawer_parent, out):
    """The Pi archive: the drawer only, fixed dates and modes."""
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(drawer_parent.rglob("*")):
            rel = p.relative_to(drawer_parent).as_posix()
            if rel.startswith(NAME + ".arospkg"):
                continue
            info = zipfile.ZipInfo(rel + ("/" if p.is_dir() else ""), (1980, 1, 1, 0, 0, 0))
            info.external_attr = ((0o40755 if p.is_dir() else 0o100755 if p.name == "fastfetch" else 0o100644) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, b"" if p.is_dir() else p.read_bytes())


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    target, version, build = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    if target not in TARGETS:
        raise RuntimeError(f"unknown target {target}")
    # "2.70.0-r1": upstream's version and this port's revision of it.
    upstream, _, rev = version.partition("-r")
    if not rev.isdigit():
        raise RuntimeError(f"version {version}: expected <upstream>-r<revision>, e.g. 2.70.0-r1")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"{NAME}-{version}-{target}.zip"
    if out.exists():
        raise RuntimeError(f"{out} exists; delivered archives are not replaced")
    with tempfile.TemporaryDirectory(prefix="fastfetch-package-") as d:
        parent = Path(d)
        stage(parent / NAME, target, version, build)
        if TARGETS[target]["requires"] is None:
            write_zip(parent, out)
        else:
            (parent / f"{NAME}.arospkg.toml").write_text(manifest(target, upstream, int(rev)))
            apkg = json.loads((ROOT / "local.json").read_text()).get("apkg_pack")
            if not apkg or not Path(apkg).is_file():
                raise RuntimeError("local.json: set apkg_pack to arospkg's tools/apkg-pack")
            subprocess.run([sys.executable, apkg, "build", parent / NAME, "--output", out,
                            "--epoch", str(EPOCH)], check=True)
            subprocess.run([sys.executable, apkg, "check", out], check=True)
    with zipfile.ZipFile(out) as z:
        if z.testzip() is not None or z.read(f"{NAME}/fastfetch") != (build / "cmake" / "fastfetch").read_bytes():
            out.unlink()
            raise RuntimeError("archive does not hold the built executable")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    with (dist / "SHA256SUMS").open("a") as f:
        f.write(f"{sha}  {out.name}\n")
    print(f"{out} {sha}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as e:
        print(f"package: {e}", file=sys.stderr)
        sys.exit(1)
