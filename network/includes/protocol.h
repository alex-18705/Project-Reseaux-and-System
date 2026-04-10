#ifndef PROTOCOL_H
#define PROTOCOL_H

#define MSG_TYPE_SIZE 32
#define PEER_ID_SIZE 64
#define JSON_SIZE 4096

typedef struct {
    char type[MSG_TYPE_SIZE]; 
    char event_json[JSON_SIZE]; // JSON object string for the event payload
} Message;

/* PARSE MESSAGE FROM PYTHON 
 * Example JSON:
 * {
 *   "type": "SEND_TO",
 *   "payload": {
 *     "target_peer_id": "peer-1",
 *     "event": { ... }
 *   }
 * }
 */
int parse_message(const char *json_str, Message *msg);
void build_game_event(char *buffer, size_t buffer_size, const char *event_json); // Python local event to C -> peer
void build_remote_event(char *buffer, size_t buffer_size, const char *event_json); // peer event to C -> Python
// void build_peer_message(char *buffer, const char *peer_id, const char *event_json);
// void build_peer_connected(char *buffer, const char *peer_id, const char *ip, int port);
// void build_peer_disconnected(char *buffer, const char *peer_id);

#endif
