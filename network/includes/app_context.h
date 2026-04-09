#ifndef APP_CONTEXT_H
#define APP_CONTEXT_H

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

#define MAX_PEERS 100
#define BUF_SIZE 1024

typedef struct {
    struct sockaddr_in addr;
    socklen_t addr_len;
    int active;
} Peer;

typedef struct {
    socket_t listen_fd; // UDP socket used to receive/send peer datagrams
    socket_t python_fd; // local IPC socket for Python connection
    Peer peers[MAX_PEERS];
    int running;
} AppContext;

void init_app_context(AppContext *ctx);

#endif
