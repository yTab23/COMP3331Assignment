#define _POSIX_C_SOURCE 200809L
#include "starter.h"

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void usage(bool server)
{
    puts(server
        ? "Usage: ./server [--port 51000] [--analysis-delay 0.5]"
        : "Usage: ./client [--host 127.0.0.1] [--port 51000] [--timeout 30]");
    puts("Times are seconds. --help prints this message.");
}

static void option_error(void)
{
    fprintf(stderr, "Invalid launch option; use --help\n");
    exit(2);
}

StarterOptions starter_options(int argc, char **argv, bool server)
{
    StarterOptions options = {"127.0.0.1", 51000, 30.0, 0.5};
    for (int i = 1; i < argc; ++i) {
        const char *key = argv[i];
        if (strcmp(key, "--help") == 0) {
            usage(server);
            exit(0);
        }
        if (++i == argc) {
            option_error();
        }
        const char *value = argv[i];
        if (!server && strcmp(key, "--host") == 0) {
            options.host = value;
            continue;
        }
        char *end;
        errno = 0;
        double number = strtod(value, &end);
        if (end == value || *end != '\0' || errno != 0 || !isfinite(number)) {
            option_error();
        }
        if (strcmp(key, "--port") == 0 && number >= 1 && number <= 65535
                && floor(number) == number) {
            options.port = (int)number;
        } else if (server && strcmp(key, "--analysis-delay") == 0 && number >= 0) {
            options.analysis_delay = number;
        } else if (!server && strcmp(key, "--timeout") == 0 && number > 0) {
            options.timeout = number;
        } else {
            option_error();
        }
    }
    return options;
}

bool starter_output(const cJSON *value)
{
    char *text = cJSON_PrintUnformatted(value);
    if (text == NULL) {
        fprintf(stderr, "JSON serialization failed\n");
        return false;
    }
    flockfile(stdout);
    bool ok = fprintf(stdout, "%s\n", text) >= 0;
    if (fflush(stdout) == EOF) {
        ok = false;
    }
    funlockfile(stdout);
    cJSON_free(text);
    if (!ok) {
        fprintf(stderr, "JSON output failed\n");
    }
    return ok;
}

static cJSON *required(cJSON *value)
{
    if (value == NULL) {
        fprintf(stderr, "JSON allocation failed\n");
        exit(1);
    }
    return value;
}

/* Transfers ownership of value to object; allocation failure is fatal. */
static void add(cJSON *object, const char *key, cJSON *value)
{
    required(value);
    if (!cJSON_AddItemToObject(object, key, value)) {
        cJSON_Delete(value);
        fprintf(stderr, "JSON allocation failed\n");
        exit(1);
    }
}

static cJSON *envelope(const cJSON *id)
{
    cJSON *message = required(cJSON_CreateObject());
    add(message, "jsonrpc", cJSON_CreateString("2.0"));
    if (id != NULL) {
        add(message, "id", cJSON_Duplicate(id, true));
    }
    return message;
}

cJSON *starter_request(const cJSON *id, const char *method,
                      const cJSON *params, const cJSON *token)
{
    cJSON *message = envelope(id);
    cJSON *body = required(cJSON_Duplicate(params, true));
    cJSON *meta = required(cJSON_CreateObject());
    add(meta, "io.modelcontextprotocol/protocolVersion", cJSON_CreateString("2026-07-28"));
    add(meta, "io.modelcontextprotocol/clientCapabilities", cJSON_CreateObject());
    if (token != NULL) {
        add(meta, "progressToken", cJSON_Duplicate(token, true));
    }
    cJSON_DeleteItemFromObjectCaseSensitive(body, "_meta");
    add(body, "_meta", meta);
    add(message, "method", cJSON_CreateString(method));
    add(message, "params", body);
    return message;
}

cJSON *starter_completed(const cJSON *id, const cJSON *fields)
{
    cJSON *message = envelope(id);
    cJSON *result = required(cJSON_Duplicate(fields, true));
    cJSON_DeleteItemFromObjectCaseSensitive(result, "resultType");
    add(result, "resultType", cJSON_CreateString("complete"));
    add(message, "result", result);
    return message;
}

cJSON *starter_error(const cJSON *id, int code, const char *message,
                    const cJSON *data)
{
    cJSON *response = envelope(id);
    cJSON *error = required(cJSON_CreateObject());
    add(error, "code", cJSON_CreateNumber(code));
    add(error, "message", cJSON_CreateString(message));
    if (data != NULL) {
        add(error, "data", cJSON_Duplicate(data, true));
    }
    add(response, "error", error);
    return response;
}

cJSON *starter_progress(const cJSON *token, int done, int total)
{
    cJSON *message = envelope(NULL);
    cJSON *params = required(cJSON_CreateObject());
    add(message, "method", cJSON_CreateString("notifications/progress"));
    add(params, "progressToken", cJSON_Duplicate(token, true));
    add(params, "progress", cJSON_CreateNumber(done));
    if (total >= 0) {
        add(params, "total", cJSON_CreateNumber(total));
    }
    add(message, "params", params);
    return message;
}
