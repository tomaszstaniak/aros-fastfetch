#!/usr/bin/env python3
"""Write packaging/Completions/fastfetch: what TAB offers after "fastfetch" in Limpet.

    completions.py

Made from the option list fastfetch itself prints its help from
(work/fastfetch/doc/help.json) and from the names of the presets the package
holds. Limpet (0.14.0 or later) reads the file from the program's drawer;
the format is described in Limpet's doc/prompt-and-completion.md.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLOURS = "black red green yellow blue magenta cyan white default"
WORD = re.compile(r"^[A-Za-z0-9_.-]+$")


def value(option, presets):
    arg = option.get("arg")
    if not arg:
        return ""
    kind = arg["type"]
    if kind == "bool":
        return " true false"
    if kind == "enum":
        words = [w for w in arg["enum"] if WORD.match(w)]
        return " " + " ".join(words) if words else " <value>"
    if kind == "color":
        return " " + COLOURS
    if kind == "path":
        return " <file>"
    if kind == "config":
        return " " + " ".join(presets)
    return " <value>"


def main():
    src = ROOT / "work" / "fastfetch"
    presets = sorted(p.stem for d in (src / "presets", ROOT / "packaging" / "presets") for p in d.glob("*.jsonc"))
    lines = ["# fastfetch: options for TAB in Limpet 0.14.0 or later.",
             "# Made by scripts/completions.py from fastfetch's doc/help.json."]
    for group in json.loads((src / "doc" / "help.json").read_text()).values():
        for option in group:
            # "logo-color-[1-9]" stands for nine options.
            m = re.match(r"^(.*)\[(\d)-(\d)\]$", option["long"])
            longs = [m.group(1) + str(n) for n in range(int(m.group(2)), int(m.group(3)) + 1)] if m else [option["long"]]
            for long in longs:
                names = ["--" + long] + (["-" + option["short"]] if option.get("short") else [])
                if not all(WORD.match(n) for n in names):
                    raise RuntimeError(f"option name not usable in a definition: {names}")
                lines.append("option " + " ".join(names) + value(option, ["none"] + presets))
    out = ROOT / "packaging" / "Completions" / "fastfetch"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"{out}: {len(lines) - 2} options")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError) as e:
        print(f"completions: {e}", file=sys.stderr)
        sys.exit(1)
