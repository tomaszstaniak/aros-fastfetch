"""Host tests of the port: the AROS output filter, the version parser and
the patch tooling. Run with `scripts/fastfetch.py test`.

The C tests compile files of work/fastfetch with the host compiler; that is
the series once `scripts/fastfetch.py verify` passes."""
import importlib.util, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "work" / "fastfetch" / "src"
CC = os.environ.get("CC", "cc")

spec = importlib.util.spec_from_file_location("fastfetch_port", ROOT / "scripts" / "fastfetch.py")
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


def build(name, sources, extra=()):
    out = Path(tempfile.mkdtemp(prefix="ff-host-")) / name
    subprocess.run([CC, "-std=c2x", "-Wall", "-Wextra", "-Werror", "-DFF_AROS_OUTPUT_IMPL",
                    "-I", SRC, "-I", ROOT / "vendor" / "limpet-sdk" / "include",
                    "-I", ROOT / "tests" / "host" / "include", *extra, *sources, "-o", out],
                   check=True)
    return out


@unittest.skipUnless((SRC / "common" / "aros" / "aros_output.c").exists() and shutil.which(CC),
                     "work/fastfetch or a host C compiler is missing")
class OutputFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = build("output_filter", [ROOT / "tests" / "host" / "output_filter.c",
                                          SRC / "common" / "aros" / "aros_output.c"])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.exe.parent)

    def run_filter(self, data, pens, latin1):
        """The same output for every split of the input into writes."""
        results = set()
        for chunk in (1, 2, 3, 5, 64, 4096):
            r = subprocess.run([self.exe, str(int(pens)), str(int(latin1)), str(chunk)],
                               input=data, capture_output=True, check=True)
            results.add(r.stdout)
        self.assertEqual(len(results), 1, results)
        return results.pop()

    def test_pens_remap_basic_colours(self):
        self.assertEqual(self.run_filter(b"\x1b[1;31mA\x1b[44;97mB\x1b[m", True, False),
                         b"\x1b[1;38;5;1mA\x1b[48;5;4;38;5;15mB\x1b[m")

    def test_pens_keep_extended_colours(self):
        data = b"\x1b[38;5;31;48;2;30;40;50mX\x1b[0m"
        self.assertEqual(self.run_filter(data, True, False), data)

    def test_other_sequences_unchanged(self):
        data = b"\x1b[?7l\x1b[2J\x1b]8;;x\x07L\x1b]8;;\x07\x1b7\x1b8"
        self.assertEqual(self.run_filter(data, True, False), data)

    def test_latin1_console(self):
        text = "Zürich – “ok” ✓ 中…".encode()
        self.assertEqual(self.run_filter(text, False, True),
                         "Zürich - \"ok\" * ?...".encode("latin-1"))

    def test_latin1_broken_utf8(self):
        self.assertEqual(self.run_filter(b"a\xe2\x82b\xffc", False, True), b"a?b?c")

    def test_latin1_sgr_left_alone_without_pens(self):
        self.assertEqual(self.run_filter(b"\x1b[31m\xc3\xa9", False, True), b"\x1b[31m\xe9")

    def test_utf8_terminal_unchanged(self):
        text = "Zürich ✓ 中".encode()
        self.assertEqual(self.run_filter(text, True, False), text)


@unittest.skipUnless((SRC / "common" / "aros" / "aros_version.c").exists() and shutil.which(CC),
                     "work/fastfetch or a host C compiler is missing")
class VersionParser(unittest.TestCase):
    def test_strings(self):
        d = Path(tempfile.mkdtemp(prefix="ff-host-"))
        try:
            harness = d / "t.c"
            harness.write_text(r'''
#include "common/aros/aros_version.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
// The one FFstrbuf call the parser makes, without the rest of fastfetch.
void ffStrbufSetNS(FFstrbuf* s, uint32_t length, const char* value) {
    free(s->chars);
    s->chars = strndup(value, length);
    s->length = length;
}
int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        FFstrbuf v = {};
        printf("%s\n", ffArosParseVersion(argv[i], strlen(argv[i]), &v) ? v.chars : "-");
        free(v.chars);
    }
    return 0;
}
''')
            # Only the parser is wanted: compile it out of aros_version.c.
            parser = d / "parser.c"
            source = (SRC / "common" / "aros" / "aros_version.c").read_text()
            start = source.index("static bool isDigit")
            end = source.index("bool ffArosFileVersion")
            parser.write_text('#include "common/aros/aros_version.h"\n' + source[start:end])
            exe = build("version", [harness, parser],
                        ["-Wno-unused-function", "-I", SRC / "3rdparty" / "yyjson"])
            cases = {" Wanderer 1.7 (12.11.2025) ": "1.7", "  Wanderer 1.7 (12.11.2025)": "1.7",
                     "shell.resource 41.4 (1.1.2026)": "41.4", "AROS Shell 41 (date)": "41",
                     " name (1.2.3)": "-", " Prog 2.10. (x)": "2.10", " v1.2 x": "-"}
            out = subprocess.run([exe, *cases], capture_output=True, text=True, check=True).stdout
            self.assertEqual(out.splitlines(), list(cases.values()))
        finally:
            shutil.rmtree(d)


class PatchTooling(unittest.TestCase):
    def test_header_fields(self):
        for field in ("Repository:", "Base:", "Problem:", "Solution:", "Scope:",
                      "Upstream-Status:", "Verification:", "Removal:"):
            self.assertIn(field, port.REQUIRED)

    def test_targets(self):
        self.assertEqual(port.TARGETS, ("aros-x86_64-abiv11-pc", "aros-x86_64-abiv1-pc",
                                        "aros-aarch64-abiv1-raspi"))

    def test_series_names_exist(self):
        for name in port.series():
            self.assertTrue((ROOT / "patches" / "fastfetch" / name).is_file(), name)

    def test_reconstruct_refuses_existing(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                port.reconstruct(Path(d))


if __name__ == "__main__":
    unittest.main()
