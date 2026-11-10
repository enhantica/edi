// SPDX-License-Identifier: BSD-3-Clause
// Recorded replies using libcurl's public C declarations, with no network implementation.
#include <curl/curl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#undef curl_easy_setopt
#undef curl_easy_getinfo

typedef size_t (*Writer)(char *, size_t, size_t, void *);
typedef struct {
    char *url;
    Writer writer;
    void *target;
    long status;
} Transfer;

int recorded_transport_ready(void) { return 3187; }
CURLcode curl_global_init(long flags) { (void)flags; return CURLE_OK; }
CURL *curl_easy_init(void) { return (CURL *)calloc(1, sizeof(Transfer)); }
void curl_easy_cleanup(CURL *handle) {
    Transfer *transfer = (Transfer *)handle;
    free(transfer->url);
    free(transfer);
}
const char *curl_easy_strerror(CURLcode code) {
    (void)code;
    return "recorded connection unavailable";
}
CURLcode curl_easy_setopt(CURL *handle, CURLoption option, ...) {
    Transfer *transfer = (Transfer *)handle;
    va_list arguments;
    va_start(arguments, option);
    if (option == CURLOPT_URL) {
        free(transfer->url);
        transfer->url = strdup(va_arg(arguments, const char *));
    } else if (option == CURLOPT_WRITEFUNCTION) {
        transfer->writer = va_arg(arguments, Writer);
    } else if (option == CURLOPT_WRITEDATA) {
        transfer->target = va_arg(arguments, void *);
    } else if (option < CURLOPTTYPE_OBJECTPOINT) {
        (void)va_arg(arguments, long);
    } else if (option < CURLOPTTYPE_FUNCTIONPOINT) {
        (void)va_arg(arguments, void *);
    } else {
        va_end(arguments);
        return CURLE_UNKNOWN_OPTION;
    }
    va_end(arguments);
    return CURLE_OK;
}
CURLcode curl_easy_getinfo(CURL *handle, CURLINFO information, ...) {
    if (information != CURLINFO_RESPONSE_CODE) return CURLE_UNKNOWN_OPTION;
    va_list arguments;
    va_start(arguments, information);
    *va_arg(arguments, long *) = ((Transfer *)handle)->status;
    va_end(arguments);
    return CURLE_OK;
}

static const char *suffix(const char *address, const char *prefix) {
    size_t size = strlen(prefix);
    return strncmp(address, prefix, size) == 0 ? address + size : NULL;
}
CURLcode curl_easy_perform(CURL *handle) {
    Transfer *transfer = (Transfer *)handle;
    const char *relative = NULL, *location = NULL;
    char tutorial[2048];
    if (!transfer->url || !transfer->writer) return CURLE_FAILED_INIT;
    relative = suffix(transfer->url, "https://raw.githubusercontent.com/enhantica/edi-data/main/");
    if (relative) location = "primary";
    if (!relative) {
        relative = suffix(transfer->url, "https://data.easydiffraction.org/");
        if (relative) location = "mirror";
    }
    if (!relative) {
        const char *part = suffix(transfer->url, "https://enhantica.github.io/edi/tutorials/");
        if (part) {
            if (snprintf(tutorial, sizeof(tutorial), "tutorials/%s", part) >= (int)sizeof(tutorial))
                return CURLE_URL_MALFORMAT;
            relative = tutorial;
            location = "tutorials";
        }
    }
    if (!relative || strstr(relative, "..") || strchr(relative, '\\') || strchr(relative, '"'))
        return CURLE_URL_MALFORMAT;
    const char *trace = getenv("EDI_REFERENCE_TRANSPORT_TRACE");
    FILE *log = trace ? fopen(trace, "a") : NULL;
    if (!log) return CURLE_WRITE_ERROR;
    fprintf(log, "{\"location\":\"%s\",\"path\":\"%s\"}\n", location, relative);
    fclose(log);
    if (strcmp(location, "primary") == 0 && getenv("EDI_REFERENCE_PRIMARY_OUTAGE"))
        return CURLE_COULDNT_CONNECT;
    char path[4096];
    const char *root = getenv("EDI_REFERENCE_TRANSPORT_ROOT");
    if (!root || snprintf(path, sizeof(path), "%s/%s", root, relative) >= (int)sizeof(path))
        return CURLE_URL_MALFORMAT;
    FILE *input = fopen(path, "rb");
    transfer->status = input ? 200 : 404;
    if (!input) return CURLE_OK;
    char buffer[4096];
    size_t size;
    while ((size = fread(buffer, 1, sizeof(buffer), input)) != 0) {
        if (transfer->writer(buffer, 1, size, transfer->target) != size) {
            fclose(input);
            return CURLE_WRITE_ERROR;
        }
    }
    int failed = ferror(input);
    fclose(input);
    return failed ? CURLE_READ_ERROR : CURLE_OK;
}
