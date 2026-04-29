#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "protocol.h"

static void clear_message(Message *msg){
    if (!msg){
        return;
    }
    msg->kind=MSG_UNKNOWN;
    msg->type[0] = '\0';
    msg->sender_peer_id[0] = '\0';
    msg->target_peer_id[0] = '\0';
    msg->payload[0] = '\0';
}

static int extract_json_string(const char *json,const char *key,char *out,size_t out_size){
    if (!json || !key || !out || out_size == 0) {
        return -1;
    }
    
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    
    const char *p = strstr(json, pattern);
    if (!p) return -1;
    
    p = strchr(p, ':');
    if (!p) return -1;
    p++;

    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') {
        p++;
    }

    if (*p != '"') return -1;
    p++;
    
    const char *end = strchr(p, '"');
    if (!end) return -1;
    
    size_t len = (size_t)(end - p);
    
    if (len >= out_size) len = out_size - 1;
    
    memcpy(out, p, len);
    out[len] = '\0';
    return 0;
}

static int extract_json_object(const char *json, const char *key, char *out,size_t out_size) {
    if (!json || !key || !out || out_size == 0) {
        return -1;
    }

    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);

    const char *p = strstr(json, pattern);
    if (!p) {
        return -1;
    }

    p = strchr(p, ':');
    if (!p) {
        return -1;
    }

    p++;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') {
        p++;
    }

    if (*p != '{') {
        return -1;
    }

    const char *start = p;
    int depth = 0;

    while (*p) {
        if (*p == '{') {
            depth++;
        } else if (*p == '}') {
            depth--;
            if (depth == 0) {
                size_t len = (size_t)(p - start + 1);
                if (len >= out_size) {
                    len = out_size - 1;
                }
                memcpy(out, start, len);
                out[len] = '\0';
                return 0;
            }
        }
        p++;
    }
    return -1;
}

MessageType message_type_from_string(const char *type){
    if(!type){
        return MSG_UNKNOWN;
    }
    if (strcmp(type, TYPE_JOIN) == 0) {
        return MSG_JOIN;
    } else if (strcmp(type, TYPE_BROADCAST) == 0) {
        return MSG_BROADCAST;
    } else if (strcmp(type, TYPE_SEND_TO) == 0) {
        return MSG_SEND_TO;
    } else if (strcmp(type, TYPE_REMOTE_EVENT) == 0) {
        return MSG_REMOTE_EVENT;
    } else if (strcmp(type, TYPE_SHUTDOWN) == 0) {
        return MSG_SHUTDOWN;
    } else if (strcmp(type, TYPE_OWNERSHIP_REQUEST) == 0) {
        return MSG_OWNERSHIP_REQUEST;
    } else if (strcmp(type, TYPE_OWNERSHIP_TRANSFER) == 0) {
        return MSG_OWNERSHIP_TRANSFER;
    } else if (strcmp(type, TYPE_OWNERSHIP_DENIED) == 0) {
        return MSG_OWNERSHIP_DENIED;
    } else if (strcmp(type, TYPE_STATE_UPDATE) == 0) {
        return MSG_STATE_UPDATE;
    } else if (strcmp(type, TYPE_OWNERSHIP_RETURN) == 0) {
        return MSG_OWNERSHIP_RETURN;
    } else if (strcmp(type, TYPE_PING) == 0) {
        return MSG_PING;
    } else if (strcmp(type, TYPE_PONG) == 0) {
        return MSG_PONG;
    } else {
        return MSG_UNKNOWN;
    }
}

// JSON -> Struct Message
int parse_message(const char *json_str, Message *msg){
    const char *p;
    if(!json_str || !msg){
        return -1;
    }

    clear_message(msg);

    p = json_str;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') {
        p++;
    }
    if (*p != '{') {
        return -1;
    }

    if (extract_json_string(json_str, "type", msg->type, sizeof(msg->type)) != 0) {
        return -1;
    }

    msg->kind = message_type_from_string(msg->type);
    if(msg->kind == MSG_UNKNOWN){
        return -1;
    }
    if (extract_json_string(json_str, "sender_id", msg->sender_peer_id, sizeof(msg->sender_peer_id)) != 0) {
        if (extract_json_string(json_str, "sender_peer_id", msg->sender_peer_id, sizeof(msg->sender_peer_id)) != 0) {
            return -1;
        }
    }
    if (extract_json_string(json_str, "target_peer_id", msg->target_peer_id, sizeof(msg->target_peer_id)) != 0) {
        return -1;
    }
    if (extract_json_object(json_str, "payload", msg->payload, sizeof(msg->payload)) != 0) {
        return -1;
    }
    
    return 0;
}

int build_message(char *buffer, size_t buffer_size, const char *type, const char *sender_id, const char *target_peer_id, const char *payload_json) {
    if(!buffer || buffer_size == 0 || !type){
        return -1;
    }

    if (sender_id == NULL) {
        sender_id = "";
    }

    if(target_peer_id == NULL){
        target_peer_id = "";
    }

    if (!payload_json || payload_json[0] == '\0') {
        payload_json = "{}";
    }

    int written = snprintf(
        buffer,
        buffer_size,
        "{"
        "\"type\":\"%s\","
        "\"sender_id\":\"%s\","
        "\"target_peer_id\":\"%s\","
        "\"payload\":%s"
        "}",
        type,
        sender_id,
        target_peer_id,
        payload_json
    );

    if (written < 0 || (size_t)written >= buffer_size) {
        return -1;
    }
    return 0;

}

int build_join_message(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json){  
    return build_message(buffer, buffer_size, "JOIN", sender_id, "", payload_json);
}

int build_broadcast_message(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json){
    return build_message(buffer, buffer_size, "BROADCAST", sender_id, "", payload_json);
}

int build_send_to_message(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json){   
    return build_message(buffer, buffer_size, "SEND_TO", sender_id, target_peer_id, payload_json);
}

int build_remote_event_message(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json){
    return build_message(buffer, buffer_size, "REMOTE_EVENT", sender_id, "", payload_json);
}

int build_shutdown_message(char *buffer, size_t buffer_size, const char *sender_id){ 
    return build_message(buffer, buffer_size, "SHUTDOWN", sender_id, "", "{}");
}

int build_ownership_request(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json){
    return build_message(buffer, buffer_size, "OWNERSHIP_REQUEST", sender_id, target_peer_id, payload_json);
}

int build_ownership_transfer(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json){
     return build_message(buffer, buffer_size, "OWNERSHIP_TRANSFER", sender_id, target_peer_id, payload_json); 
}

int build_ownership_denied(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json){
     return build_message(buffer, buffer_size, "OWNERSHIP_DENIED", sender_id, target_peer_id, payload_json); 
}

    
int build_state_update(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json){
     return build_message(buffer, buffer_size, "STATE_UPDATE", sender_id, "", payload_json); 
}

int build_ownership_return(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json){
     return build_message(buffer, buffer_size, "OWNERSHIP_RETURN", sender_id, target_peer_id, payload_json); 
}
