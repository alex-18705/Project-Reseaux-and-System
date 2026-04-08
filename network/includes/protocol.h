#ifndef PROTOCOL_H
#define PROTOCOL_H

#define MSG_TYPE_SIZE 32
#define JSON_SIZE 4096

typedef struct {
    char type[MSG_TYPE_SIZE]; 
    int target_fd;              
    char event_json[JSON_SIZE]; // JSON string for the event payload
} Message;

/* PARSE MESSAGE FROM PYTHON 
 * Example JSON:
 * {
 *   "type": "SEND_TO",
 *   "payload": {
 *     "target_fd": 7,
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
 *       "from_fd": <fd>,
 *       "ip": "<ip>",
 *       "port": <port>
 *     }
 *   }
 *
 * build_peer_disconnected:
 *   {
 *     "type": "PEER_DISCONNECTED",
 *     "payload": {
 *       "from_fd": <fd>
 *     }
 *   }
 *
 * build_peer_message:
 *   {
 *     "type": "PEER_MESSAGE",
 *     "payload": {
 *       "from_fd": <fd>,
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
void build_peer_connected(char *buffer, int fd, const char *ip, int port);
void build_peer_disconnected(char *buffer, int fd);
void build_peer_message(char *buffer, int from_fd, const char *event_json);
void build_game_event(char *buffer, const char *event_json);

#endif