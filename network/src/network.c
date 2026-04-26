#include <stdio.h>
#include <string.h>

#include "network.h"

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

socket_t udp_create_socket(const char *bind_ip, int port) {
    socket_t udp_fd;
    struct sockaddr_in addr;
    int opt = 1;
    if (port < 1 || port > 65535) {
        fprintf(stderr, "Invalid UDP port: %d\n", port);
        return (int)INVALID_FD;
    }
    udp_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (udp_fd == INVALID_FD) {
        perror("socket");
        return (int)INVALID_FD;
    }
    if (setsockopt(udp_fd, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        udp_close_socket(udp_fd);
        return (int)INVALID_FD;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    if (bind_ip && bind_ip[0] != '\0') {
        if (inet_pton(AF_INET, bind_ip, &addr.sin_addr) <= 0) {
            fprintf(stderr, "Invalid bind IP: %s\n", bind_ip);
            udp_close_socket(udp_fd);
            return (int)INVALID_FD;
        }
    } else {
        addr.sin_addr.s_addr = INADDR_ANY;
    }
    if (bind(udp_fd, (const struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        udp_close_socket(udp_fd);
        return (int)INVALID_FD;
    }
    return udp_fd;
}

int udp_send_to_addr(socket_t udp_fd, const char *msg, size_t len, const struct sockaddr_in *addr, socklen_t addr_len) {
    if (udp_fd == INVALID_FD || !msg || len == 0 || !addr) {
        return -1;
    }
    return sendto(udp_fd, msg, len, 0, (const struct sockaddr *)addr, addr_len);
}

int udp_recv_from_addr(socket_t udp_fd, char *buffer, size_t buffer_size, struct sockaddr_in *src_addr, socklen_t *src_addr_len) {
    if (udp_fd == INVALID_FD || !buffer || buffer_size <= 1 || !src_addr || !src_addr_len) {
        return -1;
    }
    return recvfrom(udp_fd, buffer, (int)(buffer_size - 1), 0, (struct sockaddr *)src_addr, src_addr_len);
}

void udp_close_socket(socket_t udp_fd) {
    if (udp_fd == INVALID_FD) {
        return;
    }
    CLOSESOCKET(udp_fd);
}
