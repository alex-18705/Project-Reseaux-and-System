#ifndef IPC_H
#define IPC_H

#include <stddef.h>
#include "app_context.h"

socket_t ipc_create_server(const char *bind_ip, int port);

socket_t ipc_accept_python(socket_t listen_fd);

int ipc_recv_from_python(AppContext *ctx, char *buffer, size_t buffer_size);

int ipc_send_to_python(AppContext *ctx, const char *msg, size_t len);

void ipc_close_socket(socket_t fd);

#endif