#ifndef APP_CONTEXT_H
#define APP_CONTEXT_H

#include <stdio.h>
#include <stdlib.h>

//Windows
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET socket_t;
typedef int socklen_t;
#define INVALID_FD INVALID_SOCKET
#else
// Linux/Unix
#include <unistd.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <arpa/inet.h>
typedef int socket_t;
#define INVALID_FD -1
#endif

#define BUF_SIZE 65535
#define MAX_PEERS 100
#define PEER_ID_SIZE 64

typedef struct {
    char peer_id[PEER_ID_SIZE];
    struct sockaddr_in addr;
    socklen_t addr_len;
    int active;
} Peer;

typedef struct {
    char local_peer_id[PEER_ID_SIZE];
    // UDP socket: C proxy <-> C proxy
    socket_t peer_fd;
    // IPC socket: C proxy <-> Python
    socket_t python_fd; 
    Peer peers[MAX_PEERS];
    int peer_count;
    int running;
} AppContext;

void init_app_context(AppContext *ctx);

void stop(const char *msg);

#endif
