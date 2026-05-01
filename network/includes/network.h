#ifndef NETWORK_H
#define NETWORK_H

#include <stddef.h>
#include "app_context.h"

socket_t udp_create_socket(const char *bind_ip, int port);

int udp_send_to_addr(socket_t udp_fd, const char *msg, size_t len, const struct sockaddr_in *addr, socklen_t addr_len);

int udp_recv_from_addr(socket_t udp_fd, char *buffer, size_t buffer_size, struct sockaddr_in *src_addr, socklen_t *src_addr_len);

void udp_close_socket(socket_t udp_fd);

#endif