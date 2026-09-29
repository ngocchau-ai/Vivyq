/*
 * launcher.c — Cautreo Desktop Studio Native Launcher
 * Ultra-lightweight C launcher (<100KB) that orchestrates:
 * 1. Cautreo Studio FastAPI Backend (Port 8765)
 * 2. Native Windows Edge App Shell (Dedicated Desktop Window, 0ms render, ~35MB RAM)
 * 3. Graceful lifecycle cleanup upon exit
 *
 * Compile: clang -O3 launcher.c -o ../cautreo-studio.exe -lws2_32 -lshlwapi
 * Author: Antigravity IDE (Sprint D1/D5)
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <shlwapi.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "shell32.lib")

#define PORT 8765
#define TARGET_URL "http://127.0.0.1:8765"

static int is_server_listening(int port) {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return 0;

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        return 0;
    }

    struct sockaddr_in client;
    client.sin_family = AF_INET;
    client.sin_port = htons((unsigned short)port);
    client.sin_addr.s_addr = inet_addr("127.0.0.1");

    // Fast non-blocking / short timeout connect
    u_long mode = 1;
    ioctlsocket(sock, FIONBIO, &mode);

    connect(sock, (struct sockaddr*)&client, sizeof(client));

    fd_set fdset;
    FD_ZERO(&fdset);
    FD_SET(sock, &fdset);
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 250000; // 250ms

    int ret = select(0, NULL, &fdset, NULL, &tv);
    closesocket(sock);
    WSACleanup();

    return (ret > 0);
}

static BOOL find_msedge(char* out_path, size_t max_len) {
    const char* paths[] = {
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    };

    for (int i = 0; i < 2; ++i) {
        if (PathFileExistsA(paths[i])) {
            strncpy(out_path, paths[i], max_len - 1);
            out_path[max_len - 1] = '\0';
            return TRUE;
        }
    }
    return FALSE;
}

int main(int argc, char* argv[]) {
    printf("====================================================\n");
    printf("  CAUTREO DESKTOP STUDIO V1.0 — NATIVE LAUNCHER\n");
    printf("====================================================\n\n");

    // 1. Check if backend is running
    PROCESS_INFORMATION backend_pi = {0};
    BOOL started_backend = FALSE;

    if (!is_server_listening(PORT)) {
        printf("[+] Starting Cautreo Desktop Studio backend on port %d...\n", PORT);

        // Get directory of current exe
        char exe_path[MAX_PATH];
        GetModuleFileNameA(NULL, exe_path, MAX_PATH);
        PathRemoveFileSpecA(exe_path);

        char cmd[MAX_PATH * 2];
        snprintf(cmd, sizeof(cmd), "python \"%s\\backend\\server.py\"", exe_path);

        STARTUPINFOA si = {0};
        si.cb = sizeof(si);
        // Run with hidden console for backend
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE;

        if (CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, exe_path, &si, &backend_pi)) {
            started_backend = TRUE;
            printf("[+] Backend spawned (PID: %lu). Waiting for ready state...\n", backend_pi.dwProcessId);

            // Wait up to 5s for server to listen
            for (int i = 0; i < 20; ++i) {
                Sleep(250);
                if (is_server_listening(PORT)) {
                    printf("[+] Backend is READY and listening on %s!\n", TARGET_URL);
                    break;
                }
            }
        } else {
            printf("[-] Warning: Failed to spawn backend automatically. Trying direct connect...\n");
        }
    } else {
        printf("[+] Backend is already running on port %d.\n", PORT);
    }

    // 2. Find Edge browser for Native App Shell
    char edge_path[MAX_PATH];
    if (!find_msedge(edge_path, sizeof(edge_path))) {
        printf("[-] Microsoft Edge not found! Opening default system browser...\n");
        ShellExecuteA(NULL, "open", TARGET_URL, NULL, NULL, SW_SHOWNORMAL);
    } else {
        printf("[+] Launching Native Desktop App Shell via Edge...\n");

        char edge_args[MAX_PATH * 3];
        snprintf(edge_args, sizeof(edge_args),
            "\"%s\" --app=\"%s\" --window-size=1320,840 --app-id=com.cautreo.studio",
            edge_path, TARGET_URL
        );

        STARTUPINFOA edge_si = {0};
        edge_si.cb = sizeof(edge_si);
        PROCESS_INFORMATION edge_pi = {0};

        if (CreateProcessA(NULL, edge_args, NULL, NULL, FALSE, 0, NULL, NULL, &edge_si, &edge_pi)) {
            printf("[+] Desktop App Window opened. Running Cautreo Studio...\n");

            // Wait for Edge window to close
            WaitForSingleObject(edge_pi.hProcess, INFINITE);

            CloseHandle(edge_pi.hProcess);
            CloseHandle(edge_pi.hThread);
            printf("[+] Desktop window closed by user.\n");
        } else {
            printf("[-] Failed to launch Edge in app mode. Fallback to ShellExecute.\n");
            ShellExecuteA(NULL, "open", TARGET_URL, NULL, NULL, SW_SHOWNORMAL);
        }
    }

    // 3. Cleanup backend if we started it
    if (started_backend && backend_pi.hProcess) {
        printf("[+] Shutting down backend process (PID: %lu)...\n", backend_pi.dwProcessId);
        TerminateProcess(backend_pi.hProcess, 0);
        CloseHandle(backend_pi.hProcess);
        CloseHandle(backend_pi.hThread);
    }

    printf("[+] Cautreo Desktop Studio exited cleanly. Farewell!\n");
    return 0;
}
