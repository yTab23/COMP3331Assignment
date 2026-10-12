#ifndef STARTER_H
#define STARTER_H

#include "support/c/student_tools.h"

typedef struct {
    const char *host; /* Borrowed from argv or a string literal. */
    int port;
    double timeout;
    double analysis_delay;
} StarterOptions;

/* Exits 0 for --help, 2 for invalid options. Times are seconds. */
StarterOptions starter_options(int argc, char **argv, bool server);

/* Borrows value; serializes, writes one whole line, and flushes under a
 * stdout lock. All application JSON output should use this function.
 * Returns false on serialization/output failure. Do not mutate value during use. */
bool starter_output(const cJSON *value);

/* Constructors borrow every input and return independent, caller-owned trees.
 * Free results with cJSON_Delete. Allocation failure prints a diagnostic and
 * exits 1. Inputs have valid shapes; these helpers do not validate them.
 * request replaces params._meta; completed replaces fields.resultType.
 * token=NULL omits progressToken. error id=NULL omits id, data=NULL omits data.
 * progress total<0 omits total. IDs/tokens retain their JSON types. */
cJSON *starter_request(const cJSON *id, const char *method,
                      const cJSON *params, const cJSON *token);
cJSON *starter_completed(const cJSON *id, const cJSON *fields);
cJSON *starter_error(const cJSON *id, int code, const char *message,
                    const cJSON *data);
cJSON *starter_progress(const cJSON *token, int done, int total);

#endif
