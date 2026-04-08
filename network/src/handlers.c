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
 * Send JSON message to Python
 */
static void send_to_python(AppContext *ctx, const char *json_msg) {
    if (ctx->python_fd == INVALID_FD) {
        return;
    }
    send(ctx->python_fd, json_msg, strlen(json_msg), 0);
    send(ctx->python_fd, "\n", 1, 0); 
}


/*
 * when a new peer connects, accept the connection, add to peer list, and notify Python
 */
void handle_new_peer(AppContext *ctx) {

    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);

    socket_t peer_fd = accept(
        ctx->listen_fd,
        (struct sockaddr*)&client_addr,
        &addr_len
    );

    if (peer_fd == INVALID_FD) {
        perror("accept");
        return;
    }

    if (add_peer(ctx, peer_fd, &client_addr) < 0) {
        printf("Max peers reached\n");
        CLOSESOCKET(peer_fd);
        return;
    }

    char json_buf[BUF_SIZE];
    build_peer_connected(json_buf, peer_fd,inet_ntoa(client_addr.sin_addr),ntohs(client_addr.sin_port));
    send_to_python(ctx, json_buf);
}


/*
 * when a peer sends data, read the data, and forward to Python. If peer disconnects, remove from peer list and notify Python
 */
void handle_peer_data(AppContext *ctx, int peer_fd) {
    char buffer[BUF_SIZE];
    int r = recv(peer_fd, buffer, sizeof(buffer) - 1, 0);

    if (r <= 0) {
        if (r == 0) {
            printf("Peer %d disconnected\n", peer_fd);
        } else {
            perror("recv peer");
        }

        int idx = find_peer_by_fd(ctx, peer_fd);

        if (idx >= 0) {
            remove_peer(ctx, idx);
        } else {
            CLOSESOCKET(peer_fd);
        }

        char json_buf[BUF_SIZE];
        build_peer_disconnected(json_buf, peer_fd);
        send_to_python(ctx, json_buf);

        return;
    }
    buffer[r] = '\0';
    char json_buf[BUF_SIZE * 2];
    build_peer_message(json_buf, peer_fd, buffer);
    send_to_python(ctx, json_buf);
}


/* Event: Python send to C*/
void handle_python_data(AppContext *ctx) {
    char buffer[BUF_SIZE * 2];
    int n = recv(ctx->python_fd, buffer, sizeof(buffer) - 1, 0);
    if (n <= 0) {
        if (n < 0) {
            perror("recv python");
        }
        return;
    }
    buffer[n] = '\0';
    Message msg;
    if (parse_message(buffer, &msg) != 0) {
        printf("Invalid message from Python: %s\n", buffer);
        return;
    }
    /*
     * BROADCAST
     */
    if (strcmp(msg.type, "BROADCAST") == 0) {
        char out[BUF_SIZE * 2];
        build_game_event(out, msg.event_json);
        broadcast(ctx, out, -1);
        return;
    }
    /*
     * SEND_TO
     */
    if (strcmp(msg.type, "SEND_TO") == 0) {
        int idx = find_peer_by_fd(ctx, msg.target_fd);
        if (idx < 0) {
            printf("Target peer %d not found\n", msg.target_fd);
            return;
        }
        char out[BUF_SIZE * 2];
        build_game_event(out, msg.event_json);
        send(ctx->peers[idx].fd, out, strlen(out), 0);
        send(ctx->peers[idx].fd, "\n", 1, 0);
        return;
    }
    /*
     * SHUTDOWN
     */
    if (strcmp(msg.type, "SHUTDOWN") == 0) {
        printf("Shutdown requested by Python\n");
        ctx->running = 0;
        return;
    }
}