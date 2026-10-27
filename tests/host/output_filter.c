/* Host test of src/common/aros/aros_output.c: the terminal answers are set
 * from the command line, the text comes from stdin in writes of a chosen
 * size, and the filtered bytes go to stdout.
 *     output_filter PENS LATIN1 CHUNK < input > output
 * PENS and LATIN1 are 0 or 1; CHUNK splits the input into writes of that
 * many bytes, so sequences cut between writes are covered. */
#include "common/aros/aros_output.h"
#include "common/aros/aros_terminal.h"

#include <stdlib.h>
#include <unistd.h>

static bool pens, latin1;

bool ffArosTerminalPens(void) { return pens; }
bool ffArosTerminalLatin1(void) { return latin1; }

int main(int argc, char** argv) {
    if (argc != 4) {
        return 2;
    }
    pens = atoi(argv[1]) != 0;
    latin1 = atoi(argv[2]) != 0;
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
