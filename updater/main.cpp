#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <thread>
#include <filesystem>
#include <fstream>
#include "update_logic.h"

#pragma comment(lib, "shell32.lib")

// ---------------------------------------------------------------------------
// Window controls
// ---------------------------------------------------------------------------
HWND hWndMain;
HWND hStatusLabel;    // primary message  (e.g. "Version 4.6.6 is available")
HWND hDetailLabel;    // secondary message (e.g. "You are running 4.6.5")
HWND hViewButton;     // "View on GitHub"
HWND hSkipButton;     // "Skip"

bool g_isSilent      = false;
bool g_isInteractive = false;

// Stored so the button handler can open it
static std::wstring g_releaseUrl;

// Window dimensions
static const int WND_W = 420;
static const int WND_H = 180;

// Control IDs
static const int ID_VIEW = 1;
static const int ID_SKIP = 2;

// ---------------------------------------------------------------------------
// WindowProc
// ---------------------------------------------------------------------------
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        // Status label — top message
        hStatusLabel = CreateWindowEx(0, L"STATIC", L"Checking for updates...",
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            10, 20, WND_W - 20, 30,
            hwnd, NULL, NULL, NULL);

        // Detail label — secondary info
        hDetailLabel = CreateWindowEx(0, L"STATIC", L"",
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            10, 60, WND_W - 20, 24,
            hwnd, NULL, NULL, NULL);

        // "View on GitHub" button — hidden until update found
        hViewButton = CreateWindowEx(0, L"BUTTON", L"View on GitHub",
            WS_CHILD | WS_VISIBLE | WS_DISABLED,
            60, 105, 130, 32,
            hwnd, (HMENU)ID_VIEW, NULL, NULL);

        // "Skip" button
        hSkipButton = CreateWindowEx(0, L"BUTTON", L"Skip",
            WS_CHILD | WS_VISIBLE,
            210, 105, 130, 32,
            hwnd, (HMENU)ID_SKIP, NULL, NULL);

        return 0;
    }
    case WM_COMMAND:
        if (LOWORD(wParam) == ID_VIEW) {
            // Open release page in default browser, then close
            if (!g_releaseUrl.empty()) {
                ShellExecuteW(NULL, L"open", g_releaseUrl.c_str(),
                              NULL, NULL, SW_SHOWNORMAL);
            }
            PostMessage(hwnd, WM_CLOSE, 0, 0);
        } else if (LOWORD(wParam) == ID_SKIP) {
            PostMessage(hwnd, WM_CLOSE, 0, 0);
        }
        break;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

// ---------------------------------------------------------------------------
// Helper: shorten an ISO 8601 date to YYYY-MM-DD
// ---------------------------------------------------------------------------
static std::string ShortDate(const std::string& iso) {
    return iso.length() >= 10 ? iso.substr(0, 10) : iso;
}

// ---------------------------------------------------------------------------
// UpdateThread: runs off the main thread so the message loop stays responsive
// ---------------------------------------------------------------------------
void UpdateThread(HWND hwnd) {
    BuildInfo local = UpdateLogic::GetBuildInfo();
    ReleaseInfo info = UpdateLogic::CheckForUpdates(local);

    if (!info.found) {
        if (g_isInteractive) {
            SetWindowText(hStatusLabel, L"Application is up to date.");
            Sleep(2000);
        }
        PostMessage(hwnd, WM_CLOSE, 0, 0);
        return;
    }

    // Update found — show the window if we were running silently
    if (g_isSilent) {
        ShowWindow(hwnd, SW_SHOWNORMAL);
        SetForegroundWindow(hwnd);
    }

    // Build the two label strings based on notify type
    std::wstring primary, secondary;

    switch (info.notify_type) {
    case NOTIFY_STABLE_AVAILABLE:
        primary = L"Version " +
                  std::wstring(info.version.begin(), info.version.end()) +
                  L" is available";
        secondary = L"You are running " +
                    std::wstring(local.version.begin(), local.version.end());
        break;

    case NOTIFY_STABLE_FROM_DEV:
        primary = L"Stable release " +
                  std::wstring(info.version.begin(), info.version.end()) +
                  L" is now out";
        secondary = L"You are running a dev build (" +
                    std::wstring(ShortDate(local.build_date).begin(),
                                 ShortDate(local.build_date).end()) +
                    L")";
        break;

    case NOTIFY_DEV_UPDATE: {
        std::string newDate  = ShortDate(info.publish_date);
        std::string yourDate = ShortDate(local.build_date);
        primary   = L"Dev build " +
                    std::wstring(newDate.begin(), newDate.end()) +
                    L" is available";
        secondary = L"Your build: " +
                    std::wstring(yourDate.begin(), yourDate.end());
        break;
    }

    default:
        primary = L"An update is available.";
        break;
    }

    SetWindowText(hStatusLabel, primary.c_str());
    SetWindowText(hDetailLabel, secondary.c_str());

    // Store the URL and enable the "View on GitHub" button
    g_releaseUrl = std::wstring(info.release_url.begin(), info.release_url.end());
    EnableWindow(hViewButton, TRUE);
}

// ---------------------------------------------------------------------------
// WinMain
// ---------------------------------------------------------------------------
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR lpCmdLine, int nCmdShow) {
    std::string cmdLine = lpCmdLine;
    if (cmdLine.find("--silent")      != std::string::npos) g_isSilent      = true;
    if (cmdLine.find("--interactive") != std::string::npos) g_isInteractive = true;

    const wchar_t CLASS_NAME[] = L"Hammer5ToolsUpdaterWindow";
    WNDCLASS wc = {};
    wc.lpfnWndProc   = WindowProc;
    wc.hInstance     = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.hCursor       = LoadCursor(NULL, IDC_ARROW);
    RegisterClass(&wc);

    hWndMain = CreateWindowEx(
        0, CLASS_NAME, L"Hammer 5 Tools \u2014 Updater",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU,
        CW_USEDEFAULT, CW_USEDEFAULT, WND_W, WND_H,
        NULL, NULL, hInstance, NULL);

    if (hWndMain == NULL) return 0;

    if (!g_isSilent || g_isInteractive) {
        ShowWindow(hWndMain, nCmdShow);
    }

    std::thread worker(UpdateThread, hWndMain);
    worker.detach();

    MSG msg = {};
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
    return 0;
}
