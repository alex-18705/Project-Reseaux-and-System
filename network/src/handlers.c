#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <windows.h>
#define CLOSESOCKET closesocket
#else
#include <unistd.h>
#include <sys/socket.h>
#define CLOSESOCKET close
#endif

#include "handlers.h"
#include "peer_manage.h"
#include "protocol.h"


/*
 * when a new peer connects, accept the connection, add to peer list, and notify Python
 */
// void handle_new_peer(AppContext *ctx) {

//     struct sockaddr_in client_addr;
//     socklen_t addr_len = sizeof(client_addr);


//     if (peer_fd == INVALID_FD) {
//         perror("accept");
//         return;
//     }

//     if (add_peer(ctx, peer_fd, &client_addr) < 0) {
//         printf("Max peers reached\n");
//         CLOSESOCKET(peer_fd);
//         return;
//     }

//     char json_buf[BUF_SIZE];
//     build_peer_connected(json_buf, peer_fd,inet_ntoa(client_addr.sin_addr),ntohs(client_addr.sin_port));
//     send_to_python(ctx, json_buf);
// }


void handle_peer_data(AppContext *ctx) {
    char buffer[BUF_SIZE];
    struct sockaddr_in src_addr;
    socklen_t addr_len = sizeof(src_addr);

    int r = recvfrom(ctx->peer_fd, buffer, sizeof(buffer), 0, (struct sockaddr *)&src_addr, &addr_len);
    if (r < 0) {
        stop("recvfrom peer");
    }

    if (r == 0) {
        printf("[C] Peer closed connection\n");
        return;
    }

    printf("[C] recv from peer: %d bytes from %s:%d\n",
           r,
           inet_ntoa(src_addr.sin_addr),
           ntohs(src_addr.sin_port));

    if (!is_known_peer(ctx, &src_addr, addr_len)) {
        printf("[C] unknown peer %s:%d, dropping packet\n",
               inet_ntoa(src_addr.sin_addr),
               ntohs(src_addr.sin_port));
        return;
    }

    if (!ctx->has_python_addr) {
        printf("[C] Python address unknown, dropping peer packet\n");
        return;
    }

    printf("[C] forward to python: %s:%d\n",
           inet_ntoa(ctx->python_addr.sin_addr),
           ntohs(ctx->python_addr.sin_port));

    int s = sendto(ctx->python_fd, buffer, r, 0, (struct sockaddr *)&ctx->python_addr, ctx->python_addr_len);
    if (s < 0) {
        stop("sendto python");
    }
}



/* Event: Python send to C*/
void handle_python_data(AppContext *ctx) {
    char buffer[BUF_SIZE + 1];
    struct sockaddr_in src_addr ;
    socklen_t addr_len = sizeof(src_addr);
    int r = recvfrom(ctx->python_fd, buffer, sizeof(buffer), 0, (struct sockaddr*)&src_addr, &addr_len);
    if (r<0){
        stop ("recvfrom python");
    }

    if (r == 0) {
        printf("[C] Python closed connection\n");
        return;
    }

    buffer[r] = '\0';

    printf("[C] recv from python: %d bytes from %s:%d\n",
           r,
           inet_ntoa(src_addr.sin_addr),
           ntohs(src_addr.sin_port));
    
    ctx->python_addr = src_addr;
    ctx->python_addr_len = addr_len;
    ctx->has_python_addr = 1;

    /* Registration packet sent by NetworkBridge.connect():
     * keep python_addr, but do not forward it to the remote proxy.
     */
    if (r == 1 && buffer[0] == '\n') {
        printf("[C] python registration packet received, not forwarding\n");
        return;
    }

    if (r >= 10 && strstr(buffer, "\"type\":\"SHUTDOWN\"") != NULL) {
        printf("[C] shutdown requested by python\n");
        ctx->running = 0;
        return;
    }

    if (ctx->peer_count == 0) {
        printf("[C] No registered peers, dropping python packet\n");
        return;
    }

    printf("[C] broadcasting to %d peer(s)\n", ctx->peer_count);

    if (broadcast_to_peers(ctx, buffer, (size_t)r) < 0) {
        stop("broadcast to peers");
    }

}
