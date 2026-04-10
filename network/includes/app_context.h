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
    char peer_id[64]; // Unique identifier for the peer (e.g., username or UUID)
} Peer;

typedef struct {
    socket_t peer_fd; // UDP socket used to receive/send peer datagrams
    socket_t python_fd; // local IPC socket for Python connection
    
    struct sockaddr_in python_addr; // Address for Python IPC
    socklen_t python_addr_len;
    int has_python_addr;

    struct sockaddr_in peer_addr; // Address for peer
    socket_t peer_addr_len;
    int has_peer_addr;

    int running;
} AppContext;

void init_app_context(AppContext *ctx);
int stop(char *msg);

#endif
