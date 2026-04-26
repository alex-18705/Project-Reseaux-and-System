#ifndef PEER_MANAGER_H
#define PEER_MANAGER_H
#include <stddef.h>
#include "app_context.h"
#include "network.h"

int add_or_update_peer(AppContext *ctx, const char *peer_id, const struct sockaddr_in *addr, socklen_t addr_len);

int find_peer_by_id(const AppContext *ctx, const char *peer_id);

int add_peer(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len);

int is_known_peer(const AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len);

int send_to_peer_id(AppContext *ctx, const char *peer_id, const char *msg, size_t len);

int broadcast_to_peers(AppContext *ctx, const char *msg, size_t len);

#endif
