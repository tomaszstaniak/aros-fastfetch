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


def charset_table(codec):
    """Unicode scalars of bytes 0x80..0xFF in `codec`, 0 where none, C1 as none."""
    values = []
    for b in range(0x80, 0x100):
        try:
            c = ord(bytes([b]).decode(codec))
        except UnicodeDecodeError:
            c = 0
        values.append(0 if c < 0xA0 else c)
    return "{ " + ", ".join(str(v) for v in values) + " }"


def build(name, sources, extra=()):
    out = Path(tempfile.mkdtemp(prefix="ff-host-")) / name
    (out.parent / "charset_tables.h").write_text(
        f"#define FF_TEST_LATIN1 {charset_table('iso8859_1')}\n"
        f"#define FF_TEST_LATIN2 {charset_table('iso8859_2')}\n")
    subprocess.run([CC, "-std=c2x", "-Wall", "-Wextra", "-Werror", "-DFF_AROS_OUTPUT_IMPL",
                    "-I", SRC, "-I", ROOT / "vendor" / "limpet-sdk" / "include",
                    "-I", ROOT / "tests" / "host" / "include", "-I", out.parent,
                    *extra, *sources, "-o", out],
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

    def run_filter(self, data, pens, charset):
        """The same output for every split of the input into writes.
        charset: 0 UTF-8 terminal, 1 ISO-8859-1, 2 ISO-8859-2 console."""
        results = set()
        for chunk in (1, 2, 3, 5, 64, 4096):
            r = subprocess.run([self.exe, str(int(pens)), str(int(charset)), str(chunk)],
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

    def test_latin1_no_control_bytes(self):
        # U+009B is CSI on an Amiga console; C0 9B is an overlong ESC; a
        # surrogate and a raw C1 byte are no characters either.
        data = b"<\xc2\x9b><\xc0\x9b><\xed\xa0\x80><\x9b>"
        out = self.run_filter(data, False, True)
        self.assertEqual(out, b"<?><?><?><?>")

    def test_latin2_console(self):
        # A Polish user's CON: (Locale prefs: ISO-8859-2): ą is 0xB1 there.
        text = "Zażółć gęślą jaźń · ■□ ─│┌".encode()
        self.assertEqual(self.run_filter(text, False, 2),
                         "Zażółć gęślą jaźń . #? -|+".encode("iso8859_2"))

    def test_latin2_has_no_latin1_only_letters(self):
        # ö is in both sets; ñ only in Latin-1, so it has no byte here.
        self.assertEqual(self.run_filter("öñ".encode(), False, 2), "ö?".encode("iso8859_2"))

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


@unittest.skipUnless((SRC / "common" / "aros" / "aros_text.h").exists() and shutil.which(CC),
                     "work/fastfetch or a host C compiler is missing")
class NativeNames(unittest.TestCase):
    """Names in the system's set (aros_charset.h) to UTF-8, with the set's
    table given by the test instead of codesets.library."""

    def convert(self, which, data):
        d = Path(tempfile.mkdtemp(prefix="ff-host-"))
        try:
            harness = d / "t.c"
            harness.write_text(r'''
#include "common/aros/aros_text.h"
#include "charset_tables.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
// The two out-of-line pieces of FFstrbuf the helper needs.
char* CHAR_NULL_PTR = "";
void ffStrbufEnsureFreeNoCheck(FFstrbuf* s, uint32_t free) {
    uint32_t size = s->length + free + 1;
    char* chars = s->allocated ? realloc(s->chars, size) : malloc(size);
    if (!s->allocated) memcpy(chars, s->chars, s->length + 1);
    s->chars = chars;
    s->allocated = size;
}
static FFArosCharset sets[] = {
    { "UTF-8", true, {} },
    { "ISO-8859-1", false, FF_TEST_LATIN1 },
    { "ISO-8859-2", false, FF_TEST_LATIN2 },
};
static int which;
const FFArosCharset* ffArosCharset(void) { return &sets[which]; }
int main(int argc, char** argv) {
    which = argc > 1 ? atoi(argv[1]) : 0;
    static char in[4096];
    ssize_t n = read(0, in, sizeof(in));
    FFstrbuf a = ffStrbufCreate();
    ffArosStrbufSetNativeN(&a, in, (size_t) n);
    fwrite(a.chars, 1, a.length, stdout);
    return 0;
}
''')
            exe = build("names", [harness], ["-Wno-unused-function", "-I", SRC / "3rdparty" / "yyjson"])
            try:
                return subprocess.run([exe, str(which)], input=data, capture_output=True, check=True).stdout
            finally:
                shutil.rmtree(exe.parent)
        finally:
            shutil.rmtree(d)

    def test_latin2_volume_name(self):
        # "Dysk ąę" as a Polish user's Shell writes it: 0xB1 is ą in
        # ISO-8859-2 (and ± in ISO-8859-1).
        name = "Dysk ąę:".encode("iso8859_2")
        self.assertEqual(self.convert(2, name), "Dysk ąę:".encode())
        self.assertEqual(self.convert(1, name), "Dysk ±ê:".encode())

    def test_latin1_name(self):
        self.assertEqual(self.convert(1, "Größe:".encode("latin-1")), "Größe:".encode())

    def test_bytes_without_a_character(self):
        # C1 bytes are no characters of a name in either set.
        self.assertEqual(self.convert(2, b"a\x85b"), "a\ufffdb".encode())

    def test_utf8_system(self):
        self.assertEqual(self.convert(0, "Łódź:".encode()), "Łódź:".encode())
        # Ill-formed: a lone continuation, an overlong form, a surrogate.
        self.assertEqual(self.convert(0, b"a\x80b\xc0\x80c\xed\xa0\x80d"),
                         "a\ufffdb\ufffd\ufffdc\ufffd\ufffd\ufffdd".encode())


def extract(path, start, end):
    """The production code between two markers of a file, compiled alone."""
    source = path.read_text()
    return source[source.index(start):source.index(end)]


@unittest.skipUnless((SRC / "logo" / "image" / "image_aros.c").exists() and shutil.which(CC),
                     "work/fastfetch or a host C compiler is missing")
class ImageScaling(unittest.TestCase):
    def test_scale_into_box(self):
        d = Path(tempfile.mkdtemp(prefix="ff-host-"))
        try:
            harness = d / "t.c"
            harness.write_text("""#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct { uint8_t* rgba; uint32_t width, height; } Picture;
""" + extract(SRC / "logo" / "image" / "image_aros.c", "// Area-average scaling", "static int writeStdout") + r'''
int main(void) {
    // 4x2 opaque: left half red, right half blue, into an 8x8 box: 8x4,
    // centred with two transparent rows above and below.
    uint8_t in[4 * 2 * 4], box[8 * 8 * 4];
    for (int i = 0; i < 8; ++i) {
        uint8_t* p = in + i * 4;
        int x = i % 4;
        p[0] = x < 2 ? 255 : 0; p[1] = 0; p[2] = x < 2 ? 0 : 255; p[3] = 255;
    }
    Picture pic = { in, 4, 2 };
    scaleInto(&pic, box, 8, 8);
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 8; ++x) {
            const uint8_t* q = box + (y * 8 + x) * 4;
            putchar(q[3] == 0 ? '.' : q[0] == 255 && q[2] == 0 ? 'R' : q[2] == 255 && q[0] == 0 ? 'B' : '?');
        }
        putchar('\n');
    }
    // Half-transparent white over a transparent pixel averages to white
    // at half alpha, not to grey.
    uint8_t in2[2 * 4] = { 255, 255, 255, 255, 0, 0, 0, 0 }, box2[4];
    Picture pic2 = { in2, 2, 1 };
    scaleInto(&pic2, box2, 1, 1);
    printf("%u %u %u %u\n", box2[0], box2[1], box2[2], box2[3]);
    return 0;
}
''')
            exe = build("scale", [harness])
            out = subprocess.run([exe], capture_output=True, text=True, check=True).stdout
            shutil.rmtree(exe.parent)
            self.assertEqual(out.splitlines(), ["." * 8] * 2 + ["RRRRBBBB"] * 4 + ["." * 8] * 2 + ["255 255 255 127"])
        finally:
            shutil.rmtree(d)


@unittest.skipUnless((SRC / "common" / "impl" / "processing_aros.c").exists() and shutil.which(CC),
                     "work/fastfetch or a host C compiler is missing")
class CommandQuoting(unittest.TestCase):
    def test_amigados_quoting(self):
        d = Path(tempfile.mkdtemp(prefix="ff-host-"))
        try:
            harness = d / "t.c"
            harness.write_text("#include <stdbool.h>\n#include <stdio.h>\n#include <string.h>\n" +
                               extract(SRC / "common" / "impl" / "processing_aros.c",
                                       "static bool appendQuoted", "const char* ffProcessSpawn") + r'''
int main(int argc, char** argv) {
    char line[64] = "";
    size_t length = 0;
    for (int i = 1; i < argc; ++i) {
        if (!appendQuoted(line, sizeof(line), &length, argv[i])) {
            puts("refused");
            return 0;
        }
    }
    puts(line);
    return 0;
}
''')
            exe = build("quote", [harness])
            run = lambda *a: subprocess.run([exe, *a], capture_output=True, text=True, check=True).stdout
            try:
                self.assertEqual(run("RAM:My Tools/echo it", "a\"b*c"), '"RAM:My Tools/echo it" "a*"b**c" \n')
                self.assertEqual(run("x\ny"), "refused\n")
                self.assertEqual(run("x" * 80), "refused\n")
            finally:
                shutil.rmtree(exe.parent)
        finally:
            shutil.rmtree(d)


class PatchTooling(unittest.TestCase):
    def test_header_fields(self):
        """Every saved patch carries every required header field."""
        for name in port.series():
            text = (ROOT / "patches" / "fastfetch" / name).read_text()
            header = text.split("\n---\n", 1)[0]
            for field in port.REQUIRED:
                self.assertIn("\n" + field, header, f"{name}: {field}")

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
