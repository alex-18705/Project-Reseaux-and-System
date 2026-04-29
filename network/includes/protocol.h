#ifndef PROTOCOL_H
#define PROTOCOL_H
#include <stddef.h>
#define MSG_TYPE_SIZE 32
#define PEER_ID_SIZE 64
#define JSON_SIZE 65535

#define TYPE_PING "PING"
#define TYPE_PONG "PONG"

#define TYPE_JOIN "JOIN"
#define TYPE_BROADCAST "BROADCAST"
#define TYPE_SEND_TO "SEND_TO"
#define TYPE_REMOTE_EVENT "REMOTE_EVENT"
#define TYPE_SHUTDOWN "SHUTDOWN"

#define TYPE_OWNERSHIP_REQUEST "OWNERSHIP_REQUEST"
#define TYPE_OWNERSHIP_TRANSFER "OWNERSHIP_TRANSFER"
#define TYPE_OWNERSHIP_DENIED "OWNERSHIP_DENIED"
#define TYPE_STATE_UPDATE "STATE_UPDATE"
#define TYPE_OWNERSHIP_RETURN "OWNERSHIP_RETURN"

typedef enum {
    MSG_UNKNOWN = 0,
    MSG_PING,
    MSG_PONG,
    MSG_JOIN,
    MSG_BROADCAST,
    MSG_SEND_TO,
    MSG_REMOTE_EVENT,
    MSG_SHUTDOWN,

    // Version 2
    MSG_OWNERSHIP_REQUEST,
    MSG_OWNERSHIP_TRANSFER,
    MSG_OWNERSHIP_DENIED,
    MSG_STATE_UPDATE,
    MSG_OWNERSHIP_RETURN
} MessageType;

typedef struct {
    MessageType kind;
    char type[MSG_TYPE_SIZE]; 
    char sender_peer_id[PEER_ID_SIZE];
    char target_peer_id[PEER_ID_SIZE];
    char payload[JSON_SIZE]; 
    // int taill_json;
} Message;

/*
  Parse a JSON message into Message struct.
  Expected format:
 {
    "type": "BROADCAST",
    "sender__peer_id": "player_A",
    "target_peer_id": "player_B",
    "payload": {
        "event_type": "STATE_UPDATE",
        "entity_id": "unit_A1",
        "state": {
            "x": 1,
            "y": 2,
            "hp": 100
        }
    }
 */

MessageType message_type_from_string(const char *type);

int parse_message(const char *json_str, Message *msg);

int build_message(char *buffer,size_t buffer_size,const char *type,const char *sender_id,const char *target_peer_id,const char *payload_json);

// Version 1
 int build_join_message(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json);

int build_broadcast_message(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json);

int build_send_to_message(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json);

int build_remote_event_message(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json);

int build_shutdown_message(char *buffer, size_t buffer_size, const char *sender_id);

/* Version 2 */
int build_ownership_request(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json);

int build_ownership_transfer(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json);

int build_ownership_denied(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json);

int build_state_update(char *buffer, size_t buffer_size, const char *sender_id, const char *payload_json);

int build_ownership_return(char *buffer, size_t buffer_size, const char *sender_id, const char *target_peer_id, const char *payload_json);
 
#endif
