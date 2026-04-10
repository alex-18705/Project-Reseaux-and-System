#ifndef PEER_MANAGER_H
#define PEER_MANAGER_H

#include "app_context.h"

void set_peer_addr(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len);
void set_python_addr(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len);
int send_to_peer(AppContext *ctx, const char *msg, size_t len);
int send_to_python(AppContext *ctx, const char *msg, size_t len);

#endif
