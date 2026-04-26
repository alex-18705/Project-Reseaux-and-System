#include <stdio.h>
#include <string.h>

#include "ipc.h"

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#define CLOSESOCKET closesocket
#else
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#define CLOSESOCKET close
#endif

socket_t ipc_create_server(const char *bind_ip, int port) {
    socket_t listen_fd;
    struct sockaddr_in addr;
    int opt = 1;
    if (port < 1 || port > 65535) {
        fprintf(stderr, "Invalid IPC port: %d\n", port);
        return INVALID_FD;
    }
    listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd == INVALID_FD) {
        perror("socket");
        return INVALID_FD;
    }
    if (setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        ipc_close_socket(listen_fd);
        return INVALID_FD;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    if (bind_ip && bind_ip[0] != '\0') {
        if (inet_pton(AF_INET, bind_ip, &addr.sin_addr) <= 0) {
            fprintf(stderr, "Invalid IPC bind IP: %s\n", bind_ip);
            ipc_close_socket(listen_fd);
            return INVALID_FD;
        }
    } else {
        addr.sin_addr.s_addr = INADDR_ANY;
    }
    if (bind(listen_fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        ipc_close_socket(listen_fd);
        return INVALID_FD;
    }
    if (listen(listen_fd, 1) < 0) {
        perror("listen");
        ipc_close_socket(listen_fd);
        return INVALID_FD;
    }
    return listen_fd;
}

socket_t ipc_accept_python(socket_t listen_fd) {
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    socket_t client_fd;
    if (listen_fd == INVALID_FD) {
        return INVALID_FD;
    }
    client_fd = accept(listen_fd, (struct sockaddr *)&client_addr, &client_addr_len);
    if (client_fd == INVALID_FD) {
        perror("accept");
        return INVALID_FD;
    }
    return client_fd;
}

int ipc_recv_from_python(AppContext *ctx, char *buffer, size_t buffer_size) {
    size_t count = 0;
    if (!ctx || ctx->python_fd == INVALID_FD || !buffer || buffer_size <= 1) {
        return -1;
    }
    while (count < buffer_size - 1) {
        char ch;
        int received = recv(ctx->python_fd, &ch, 1, 0);
        if (received < 0) {
            perror("recv python");
            return -1;
        }
        if (received == 0) {
            if (count == 0) {
                buffer[0] = '\0';
                return 0;
            }
            break;
        }
        buffer[count++] = ch;
        if (ch == '\n') {
            break;
        }
    }
    buffer[count] = '\0';
    return (int)count;
}

int ipc_send_to_python(AppContext *ctx, const char *msg, size_t len) {
    if (!ctx || ctx->python_fd == INVALID_FD || !msg || len == 0) {
        return -1;
    }
    return send(ctx->python_fd, msg, (int)len, 0);
}

void ipc_close_socket(socket_t fd) {
    if (fd == INVALID_FD) {
        return;
    }
    CLOSESOCKET(fd);
}
