#ifndef STUDENT_TOOLS_H
#define STUDENT_TOOLS_H

#include <stdbool.h>
#include <stddef.h>
#include "vendor/cJSON.h"

/* Lengths exclude any terminating NUL. Caller owns returned trees. */
cJSON *student_parse_json(const char *text, size_t length);

/* Validate a loaded dataset once before calling any computation helper.
 * Input arrays are already chronological, as in the supplied readings.json. */
bool student_valid_dataset(const cJSON *dataset);

typedef enum {
    STUDENT_OK,
    STUDENT_INVALID_ARGUMENT,
    STUDENT_CANCELLED,
    STUDENT_NO_MEMORY,
    STUDENT_COMPUTATION_ERROR
} StudentStatus;

typedef struct {
    StudentStatus status;
    cJSON *json;          /* Owned result on success, NULL on failure. */
    const char *error;   /* Static string, do not free. NULL on success. */
} StudentResult;

/* Inputs are borrowed, never modified. Results contain independent copies. */
StudentResult get_reading(const cJSON *dataset, const cJSON *arguments);
StudentResult get_history(const cJSON *dataset, const cJSON *arguments);

/* Both hooks are required and run synchronously on the caller's thread.
 * wait_stop(context, seconds) waits up to seconds and returns true if cancelled.
 * It also supports seconds=0, for the final cancellation check. Caller owns
 * scheduling, interruptible waiting, and synchronization of shared stop state. */
typedef bool (*StudentWaitStop)(void *context, double seconds);
typedef void (*StudentProgress)(void *context, int done, int total);
StudentResult analyse_readings(const cJSON *dataset, const cJSON *arguments,
                               double step_delay, StudentProgress progress,
                               StudentWaitStop wait_stop, void *context);

#endif
