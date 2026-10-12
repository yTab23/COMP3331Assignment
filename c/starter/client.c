#define _POSIX_C_SOURCE 200809L
#include "starter.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    StarterOptions options = starter_options(argc, argv, false);
    (void)options;
    char *line = NULL;
    size_t capacity = 0;
    ssize_t length;
    while ((length = getline(&line, &capacity, stdin)) >= 0) {
        cJSON *command = student_parse_json(line, (size_t)length);
        if (!cJSON_IsObject(command)) {
            fprintf(stderr, "Expected one JSON command object per line\n");
            cJSON_Delete(command);
            free(line);
            return 2;
        }
        /* Student: dispatch discover/list/call/cancel/wait here. Own ids,
         * tokens, sockets, HTTP sending/decoding, SSE parsing, response
         * matching, connection reuse, active calls, deadlines and cancellation.
         * At EOF drain active calls and close connections. Do not report
         * started, idle or success until the corresponding work is implemented. */
        cJSON *event = cJSON_CreateObject();
        bool ok = event != NULL
            && cJSON_AddStringToObject(event, "event", "input_error") != NULL
            && cJSON_AddStringToObject(event, "message", "starter-not-implemented") != NULL;
        if (!ok) {
            fprintf(stderr, "JSON allocation failed\n");
        } else {
            ok = starter_output(event);
        }
        cJSON_Delete(event);
        /* This loop owns command, including all child pointers. A future worker
         * needs an independent copy, or an explicit ownership transfer that
         * removes this delete and makes the worker responsible for freeing it. */
        cJSON_Delete(command);
        if (!ok) {
            free(line);
            return 1;
        }
    }
    free(line);
    if (ferror(stdin)) {
        perror("Command input failed");
        return 1;
    }
    fprintf(stderr, "starter-not-implemented: client networking and EOF cleanup\n");
    return 1;
}
