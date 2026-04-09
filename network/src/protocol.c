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

/* precise target peer identifier of message*/
static int extract_target_peer_id(const char *json_str, char *peer_id_buf, size_t buf_size) {
    const char *p = strstr(json_str, "\"target_peer_id\"");
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
    if (len >= buf_size) {
        len = buf_size - 1;
    }
    strncpy(peer_id_buf, p, len);
    peer_id_buf[len] = '\0';
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

    if (strcmp(msg->type, "SEND_TO") == 0) {
        if (extract_target_peer_id(json_str, msg->target_peer_id, sizeof(msg->target_peer_id)) != 0) {
            return -1;
        }
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

/*Build message C to Python when peer connected*/
void build_peer_connected(char *buffer, const char *peer_id, const char *ip, int port) {
    sprintf(buffer, "{\"type\":\"PEER_CONNECTED\",\"payload\":{\"peer_id\":\"%s\",\"ip\":\"%s\",\"port\":%d}}", peer_id ? peer_id : "", ip ? ip : "", port);
}

/* Build message C to Python when peer disconnected*/
void build_peer_disconnected(char *buffer, const char *peer_id) {
    sprintf(buffer,"{\"type\":\"PEER_DISCONNECTED\",\"payload\":{\"peer_id\":\"%s\"}}", peer_id ? peer_id : "");
}

/*Build message C to Python when peer send message*/
void build_peer_message(char *buffer, const char *peer_id, const char *event_json) {
    sprintf(buffer, "{\"type\":\"PEER_MESSAGE\",\"payload\":{\"peer_id\":\"%s\",\"event\":%s}}", peer_id ? peer_id : "", event_json ? event_json : "{}" );
}

/* Build message C to peer*/
void build_game_event(char *buffer, const char *event_json) {
    sprintf(buffer, "{\"type\":\"GAME_EVENT\",\"payload\":{\"event\":%s}}", event_json ? event_json : "{}");
}
