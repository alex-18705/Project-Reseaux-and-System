#ifndef PROTOCOL_H
#define PROTOCOL_H

#define MSG_TYPE_SIZE 32
#define PEER_ID_SIZE 64
#define JSON_SIZE 4096

typedef struct {
    char type[MSG_TYPE_SIZE]; 
    char target_peer_id[PEER_ID_SIZE];
    char event_json[JSON_SIZE]; // JSON string for the event payload
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

/*BUILD MESSAGE FROM C TO PYTHON 
*
 * build_peer_connected:
 *   {
 *     "type": "PEER_CONNECTED",
 *     "payload": {
 *       "peer_id": "<peer-id>",
 *       "ip": "<ip>",
 *       "port": <port>
 *     }
 *   }
 *
 * build_peer_disconnected:
 *   {
 *     "type": "PEER_DISCONNECTED",
 *     "payload": {
 *       "peer_id": "<peer-id>"
 *     }
 *   }
 *
 * build_peer_message:
 *   {
 *     "type": "PEER_MESSAGE",
 *     "payload": {
 *       "peer_id": "<peer-id>",
 *       "event": { ... }
 *     }
 *   }
 *
 * build_game_event:
 *   {
 *     "type": "GAME_EVENT",
 *     "payload": {
 *       "event": { ... }
 *     }
 *   }
*/
void build_peer_connected(char *buffer, const char *peer_id, const char *ip, int port);
void build_peer_disconnected(char *buffer, const char *peer_id);
void build_peer_message(char *buffer, const char *peer_id, const char *event_json);
void build_game_event(char *buffer, const char *event_json);

#endif
