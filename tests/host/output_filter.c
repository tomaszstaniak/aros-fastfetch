/* Host test of src/common/aros/aros_output.c: the terminal answers are set
 * from the command line, the text comes from stdin in writes of a chosen
 * size, and the filtered bytes go to stdout.
 *     output_filter PENS SET CHUNK < input > output
 * PENS is 0 or 1. SET is the 8-bit set the console takes: 0 none (UTF-8),
 * 1 ISO-8859-1, 2 ISO-8859-2 (tables from charset_tables.h, which the test
 * writes from Python's codecs). CHUNK splits the input into writes of that
 * many bytes, so sequences cut between writes are covered. */
#include "common/aros/aros_output.h"
#include "common/aros/aros_terminal.h"
#include "common/aros/aros_charset.h"
#include "charset_tables.h"

#include <stdlib.h>
#include <unistd.h>

static bool pens;
static FFArosCharset latin1 = { "ISO-8859-1", false, FF_TEST_LATIN1 };
static FFArosCharset latin2 = { "ISO-8859-2", false, FF_TEST_LATIN2 };
static const FFArosCharset* set;

bool ffArosTerminalPens(void) { return pens; }
const FFArosCharset* ffArosTerminalCharset(void) { return set; }

int main(int argc, char** argv) {
    if (argc != 4) {
        return 2;
    }
    pens = atoi(argv[1]) != 0;
    int which = atoi(argv[2]);
    set = which == 1 ? &latin1 : which == 2 ? &latin2 : nullptr;
    size_t chunk = (size_t) atoi(argv[3]);
    static char input[1 << 16];
    size_t length = 0;
    ssize_t n;
    while ((n = read(0, input + length, sizeof(input) - length)) > 0) {
        length += (size_t) n;
    }
    for (size_t i = 0; i < length; i += chunk) {
        ffArosFwrite(input + i, 1, length - i < chunk ? length - i : chunk, stdout);
    }
    ffArosFflush(stdout);
    return 0;
}
