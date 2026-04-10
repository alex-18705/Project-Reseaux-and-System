#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "protocol.h"

/* precise type of message*/
static int extract_type(const char *json_str, char *type_buf, size_t buf_size) {
    const char *p = strstr(json_str, "\"type\"");
    if (!p) {
        return -1;
    }
    p = strchr(p, ':');
    if (!p) {
        return -1;
    }
    p++;

    while (*p == ' ' || *p == '\t') {
        p++;
    }
    if (*p != '"') {
        return -1;
    }
    p++;
    const char *end = strchr(p, '"');
    if (!end) {
        return -1;
    }

    size_t len = (size_t)(end - p);
    if (len >= buf_size){
        len = buf_size - 1;
    }
    strncpy(type_buf, p, len);
    type_buf[len] = '\0';
    return 0;
}

/* precise event_json of message*/
static int extract_event_json(const char *json_str, char *event_buf, size_t buf_size) {
    if (!json_str || !event_buf || buf_size == 0) {
        return -1;
    }

    const char *event_key = strstr(json_str, "\"event\"");
    if (!event_key) {
        return -1;
    }

    const char *colon = strchr(event_key, ':');
    if (!colon) {
        return -1;
    }

    const char *p = colon + 1;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') {
        p++;
    }

    if (*p != '{') {
        return -1;
    }

    const char *start = p;
    int brace_depth = 0;

    while (*p) {
        if (*p == '{') {
            brace_depth++;
        } else if (*p == '}') {
            brace_depth--;
            if (brace_depth == 0) {
                p++;  
                break;
            }
        }
        p++;
    }

    if (brace_depth != 0) {
        return -1;
    }

    size_t length = (size_t)(p - start);
    if (length >= buf_size) {
        length = buf_size - 1;
    }

    memcpy(event_buf, start, length);
    event_buf[length] = '\0';

    return 0;
}

/* Parse message from Python*/
int parse_message(const char *json_str, Message *msg) {
    if (!json_str || !msg) {
        return -1;
    }

    memset(msg, 0, sizeof(Message));

    if (extract_type(json_str, msg->type, sizeof(msg->type)) != 0) {
        return -1;
    }

    if (strcmp(msg->type, "GAME_EVENT") == 0 || strcmp(msg->type, "REMOTE_EVENT") == 0) {
        if (extract_event_json(json_str, msg->event_json, sizeof(msg->event_json)) != 0) {
            return -1;
        }
        return 0;
    }

    if (strcmp(msg->type, "BROADCAST") == 0) {
        if (extract_event_json(json_str, msg->event_json, sizeof(msg->event_json)) != 0) {
            return -1;
        }
        return 0;
    }

    if (strcmp(msg->type, "SHUTDOWN") == 0) {
        return 0;
    }
    
    return -1;
}

/* Build message C to peer*/
void build_game_event(char *buffer, size_t buffer_size, const char *event_json) {
    if (buffer == NULL || buffer_size == 0) {
        return;
    }
    snprintf(buffer, buffer_size, "{\"type\":\"GAME_EVENT\",\"payload\":{\"event\":%s}}", event_json ? event_json : "{}");
}

/* Build message C to Python*/
void build_remote_event(char *buffer, size_t buffer_size, const char *event_json){
    if (buffer == NULL || buffer_size == 0) {
        return;
    }
    snprintf(buffer, buffer_size, "{\"type\":\"REMOTE_EVENT\",\"payload\":{\"event\":%s}}", event_json ? event_json : "{}");
}