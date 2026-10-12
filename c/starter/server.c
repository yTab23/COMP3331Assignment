#include "starter.h"

#include <stdio.h>

int main(int argc, char **argv)
{
    StarterOptions options = starter_options(argc, argv, true);
    (void)options;
    /* Student: load support/data/readings.json and support/schemas/tools.json.
     * Validate the dataset once, then keep it read-only. Bind a TCP listener
     * to 127.0.0.1 at options.port. Own accept/read/write, HTTP framing,
     * method/tool dispatch to student_tools.h, JSON/SSE responses,
     * connection reuse and cleanup. For analysis use options.analysis_delay.
     * Own per-connection work and stop state; connect progress and wait/stop
     * hooks to that call's transport and stop computation on disconnect.
     * Free loaded trees and StudentResult.json when their users finish. */
    fprintf(stderr, "starter-not-implemented: server networking and dispatch\n");
    return 1;
}
