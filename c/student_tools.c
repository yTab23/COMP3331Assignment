#include "student_tools.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *skip_space(const char *p, const char *end)
{
    while (p < end && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) {
        ++p;
    }
    return p;
}

cJSON *student_parse_json(const char *text, size_t length)
{
    if (text == NULL || length == 0 || memchr(text, '\0', length) != NULL) {
        return NULL;
    }
    /* cJSON stores C strings without lengths. Reject escaped NUL rather than
     * silently aliasing a station or argument name with a truncated string. */
    for (size_t i = 0; i < length; ++i) {
        if (text[i] == '\\' && ++i < length
            && length - i >= 5 && memcmp(text + i, "u0000", 5) == 0) {
            return NULL;
        }
    }
    const char *end = NULL;
    cJSON *json = cJSON_ParseWithLengthOpts(text, length, &end, false);
    if (json != NULL && skip_space(end, text + length) != text + length) {
        cJSON_Delete(json);
        return NULL;
    }
    return json;
}

bool student_valid_dataset(const cJSON *dataset)
{
    if (!cJSON_IsObject(dataset) || dataset->child == NULL) {
        return false;
    }
    const cJSON *records = NULL;
    cJSON_ArrayForEach(records, dataset) {
        if (!cJSON_IsArray(records) || records->child == NULL) {
            return false;
        }
        const cJSON *record = NULL;
        cJSON_ArrayForEach(record, records) {
            const cJSON *temperature = cJSON_GetObjectItemCaseSensitive(record, "temperature_c");
            if (!cJSON_IsObject(record) || !cJSON_IsNumber(temperature)
                || !isfinite(temperature->valuedouble)) {
                return false;
            }
        }
    }
    return true;
}

static StudentResult failure(StudentStatus status, const char *message)
{
    return (StudentResult){status, NULL, message};
}

static StudentResult no_memory(cJSON *partial)
{
    cJSON_Delete(partial);
    return failure(STUDENT_NO_MEMORY, "Allocation failed");
}

static const char *records_for(const cJSON *dataset, const cJSON *args,
                              bool history, const char **station, const cJSON **records)
{
    if (!cJSON_IsObject(args) || cJSON_GetArraySize(args) != (history ? 2 : 1)) {
        return "Incorrect tool argument fields";
    }
    const cJSON *item = NULL;
    bool found_station = false;
    bool found_limit = false;
    cJSON_ArrayForEach(item, args) {
        if (strcmp(item->string, "station_id") == 0 && !found_station) {
            found_station = true;
        } else if (history && strcmp(item->string, "limit") == 0 && !found_limit) {
            found_limit = true;
        } else {
            return "Incorrect tool argument fields";
        }
    }
    item = cJSON_GetObjectItemCaseSensitive(args, "station_id");
    if (!cJSON_IsString(item)) {
        return "Unknown station_id";
    }
    *station = item->valuestring;
    *records = cJSON_GetObjectItemCaseSensitive(dataset, *station);
    return *records == NULL ? "Unknown station_id" : NULL;
}

static cJSON *result_for(const char *station)
{
    cJSON *result = cJSON_CreateObject();
    if (result != NULL && cJSON_AddStringToObject(result, "station_id", station) == NULL) {
        cJSON_Delete(result);
        return NULL;
    }
    return result;
}

StudentResult get_reading(const cJSON *dataset, const cJSON *arguments)
{
    const char *station = NULL;
    const cJSON *records = NULL;
    const char *error = records_for(dataset, arguments, false, &station, &records);
    if (error != NULL) {
        return failure(STUDENT_INVALID_ARGUMENT, error);
    }
    cJSON *result = result_for(station);
    if (result == NULL) {
        return no_memory(NULL);
    }
    const cJSON *last = records->child;
    while (last->next != NULL) {
        last = last->next;
    }
    cJSON *copy = cJSON_Duplicate(last, true);
    if (copy == NULL || !cJSON_AddItemToObject(result, "reading", copy)) {
        cJSON_Delete(copy);
        return no_memory(result);
    }
    return (StudentResult){STUDENT_OK, result, NULL};
}

StudentResult get_history(const cJSON *dataset, const cJSON *arguments)
{
    const char *station = NULL;
    const cJSON *records = NULL;
    const char *error = records_for(dataset, arguments, true, &station, &records);
    if (error != NULL) {
        return failure(STUDENT_INVALID_ARGUMENT, error);
    }
    const cJSON *limit = cJSON_GetObjectItemCaseSensitive(arguments, "limit");
    if (!cJSON_IsNumber(limit) || !isfinite(limit->valuedouble)
        || limit->valuedouble < 1 || limit->valuedouble > 1000
        || floor(limit->valuedouble) != limit->valuedouble) {
        return failure(STUDENT_INVALID_ARGUMENT, "limit must be an integer from 1 to 1000");
    }
    cJSON *result = result_for(station);
    cJSON *history = result == NULL ? NULL : cJSON_AddArrayToObject(result, "readings");
    if (history == NULL) {
        return no_memory(result);
    }
    int skip = cJSON_GetArraySize(records) - (int)limit->valuedouble;
    const cJSON *record = NULL;
    cJSON_ArrayForEach(record, records) {
        if (skip > 0) {
            --skip;
            continue;
        }
        cJSON *copy = cJSON_Duplicate(record, true);
        if (copy == NULL || !cJSON_AddItemToArray(history, copy)) {
            cJSON_Delete(copy);
            return no_memory(result);
        }
    }
    return (StudentResult){STUDENT_OK, result, NULL};
}

StudentResult analyse_readings(const cJSON *dataset, const cJSON *arguments,
                               double step_delay, StudentProgress progress,
                               StudentWaitStop wait_stop, void *context)
{
    const char *station = NULL;
    const cJSON *records = NULL;
    const char *error = records_for(dataset, arguments, false, &station, &records);
    if (error != NULL) {
        return failure(STUDENT_INVALID_ARGUMENT, error);
    }
    if (!isfinite(step_delay) || step_delay < 0 || progress == NULL || wait_stop == NULL) {
        return failure(STUDENT_COMPUTATION_ERROR, "Invalid analysis hooks or delay");
    }
    double total = 0;
    int done = 0;
    int count = cJSON_GetArraySize(records);
    const cJSON *record = NULL;
    cJSON_ArrayForEach(record, records) {
        if (wait_stop(context, step_delay)) {
            return failure(STUDENT_CANCELLED, "Cancelled");
        }
        total += cJSON_GetObjectItemCaseSensitive(record, "temperature_c")->valuedouble;
        progress(context, ++done, count);
    }
    if (wait_stop(context, 0)) {
        return failure(STUDENT_CANCELLED, "Cancelled");
    }
    if (!isfinite(total)) {
        return failure(STUDENT_COMPUTATION_ERROR, "Temperature sum is not finite");
    }
    /* Decimal conversion rounds the binary double to two places, without the
     * extra multiplication rounding in round(mean * 100) / 100. */
    char rounded[512];
    int length = snprintf(rounded, sizeof rounded, "%.2f", total / done);
    if (length < 0 || (size_t)length >= sizeof rounded) {
        return failure(STUDENT_COMPUTATION_ERROR, "Mean conversion failed");
    }
    double mean = strtod(rounded, NULL);
    cJSON *result = result_for(station);
    if (result == NULL || cJSON_AddNumberToObject(result, "count", done) == NULL
        || cJSON_AddNumberToObject(result, "mean_temperature_c", mean) == NULL) {
        return no_memory(result);
    }
    return (StudentResult){STUDENT_OK, result, NULL};
}
