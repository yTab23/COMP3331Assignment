#define _POSIX_C_SOURCE 200809L
#include "student_tools.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static cJSON *load_dataset(const char *path)
{
    const size_t maximum = 1024 * 1024;
    FILE *file = fopen(path, "rb");
    if (file == NULL) {
        perror("Dataset open failed");
        return NULL;
    }
    char *text = malloc(maximum + 1);
    if (text == NULL) {
        fclose(file);
        return NULL;
    }
    size_t length = fread(text, 1, maximum + 1, file);
    bool failed = ferror(file) != 0 || length > maximum;
    if (fclose(file) != 0) {
        failed = true;
    }
    cJSON *dataset = failed ? NULL : student_parse_json(text, length);
    free(text);
    if (!student_valid_dataset(dataset)) {
        cJSON_Delete(dataset);
        return NULL;
    }
    return dataset;
}

typedef struct {
    int done;
    int cancel_after;
} DemoState;

static void progress(void *context, int done, int total)
{
    DemoState *state = context;
    state->done = done;
    fprintf(stderr, "progress %d/%d\n", done, total);
}

static bool wait_stop(void *context, double seconds)
{
    const DemoState *state = context;
    if (state->cancel_after >= 0 && state->done >= state->cancel_after) {
        return true;
    }
    struct timespec delay = {(time_t)seconds, (long)((seconds - (time_t)seconds) * 1e9)};
    while (nanosleep(&delay, &delay) != 0) {
        if (errno != EINTR) {
            perror("Wait failed");
            exit(1);
        }
    }
    return false;
}

static bool integer_option(const char *text, int maximum, int *out)
{
    if (*text == '\0') {
        return false;
    }
    int value = 0;
    for (const char *p = text; *p != '\0'; ++p) {
        if (*p < '0' || *p > '9' || value > maximum / 10) {
            return false;
        }
        value = value * 10 + (*p - '0');
        if (value > maximum) {
            return false;
        }
    }
    *out = value;
    return true;
}

int main(int argc, char **argv)
{
    int delay_ms = 0;
    DemoState state = {0, -1};
    if (argc < 4 || argc > 6
        || (strcmp(argv[2], "quick") != 0 && strcmp(argv[2], "history") != 0
            && strcmp(argv[2], "analysis") != 0)
        || (argc > 4 && strcmp(argv[2], "analysis") != 0)
        || (argc > 4 && !integer_option(argv[4], 60000, &delay_ms))
        || (argc > 5 && !integer_option(argv[5], 1000, &state.cancel_after))) {
        fprintf(stderr, "Usage: %s DATASET quick|history|analysis 'ARGS_JSON' [DELAY_MS [CANCEL_AFTER]]\n", argv[0]);
        return 64;
    }
    cJSON *dataset = load_dataset(argv[1]);
    if (dataset == NULL) {
        fprintf(stderr, "Invalid or unreadable dataset (maximum 1 MiB)\n");
        return 1;
    }
    cJSON *arguments = student_parse_json(argv[3], strlen(argv[3]));
    if (arguments == NULL) {
        fprintf(stderr, "Invalid JSON arguments\n");
        cJSON_Delete(dataset);
        return 4;
    }
    StudentResult result;
    if (strcmp(argv[2], "quick") == 0) {
        result = get_reading(dataset, arguments);
    } else if (strcmp(argv[2], "history") == 0) {
        result = get_history(dataset, arguments);
    } else {
        result = analyse_readings(dataset, arguments, delay_ms / 1000.0,
                                  progress, wait_stop, &state);
    }
    int exit_code = 0;
    if (result.status != STUDENT_OK) {
        fprintf(stderr, "%s\n", result.error);
        exit_code = result.status == STUDENT_INVALID_ARGUMENT ? 2
                    : result.status == STUDENT_CANCELLED ? 3 : 1;
    } else {
        char *text = cJSON_PrintUnformatted(result.json);
        if (text == NULL) {
            fprintf(stderr, "Serialization failed\n");
            exit_code = 1;
        } else {
            if (puts(text) == EOF || fflush(stdout) == EOF) {
                exit_code = 1;
            }
            cJSON_free(text);
        }
    }
    cJSON_Delete(result.json);
    cJSON_Delete(arguments);
    cJSON_Delete(dataset);
    return exit_code;
}
