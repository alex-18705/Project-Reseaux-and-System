#ifndef PROTOCOL_H
#define PROTOCOL_H

#define MSG_TYPE_SIZE 32
#define JSON_SIZE 4096

typedef struct {
    char type[MSG_TYPE_SIZE]; 
    int target_fd;              
    char event_json[JSON_SIZE]; 
} Message;

/* PARSE MESSAGE FROM PYTHON */
int parse_message(const char *json_str, Message *msg);

/*BUILD MESSAGE FROM C TO PYTHON */
void build_peer_connected(char *buffer, int fd, const char *ip, int port);
void build_peer_disconnected(char *buffer, int fd);
void build_peer_message(char *buffer, int from_fd, const char *event_json);
void build_game_event(char *buffer, const char *event_json);

#endif