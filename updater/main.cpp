#include <windows.h>
#include <shellapi.h>
#include <commctrl.h>
#include <string>
#include <thread>
#include <filesystem>
#include "update_logic.h"

#pragma comment(lib, "comctl32.lib")

// Window controls
HWND hWndMain;
HWND hProgressBar;
HWND hStatusLabel;
HWND hUpdateButton;

const wchar_t* CURRENT_VERSION = L"5.0.0"; // Should be synced with common.py somehow or passed in

LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
        case WM_CREATE: {
            hStatusLabel = CreateWindowEx(0, L"STATIC", L"Checking for updates...", WS_CHILD | WS_VISIBLE | SS_CENTER,
                10, 20, 280, 20, hwnd, NULL, NULL, NULL);
            hProgressBar = CreateWindowEx(0, PROGRESS_CLASS, NULL, WS_CHILD | WS_VISIBLE | PBS_SMOOTH,
                10, 50, 280, 25, hwnd, NULL, NULL, NULL);
            hUpdateButton = CreateWindowEx(0, L"BUTTON", L"Update Now", WS_CHILD | WS_VISIBLE | WS_DISABLED,
                100, 90, 100, 30, hwnd, (HMENU)1, NULL, NULL);
            return 0;
        }
        case WM_COMMAND:
            if (LOWORD(wParam) == 1) { // Update button
                EnableWindow(hUpdateButton, FALSE);
                // Start update thread...
                return 0;
            }
            break;
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

void UpdateThread(HWND hwnd) {
    // 1. Check version
    ReleaseInfo info = UpdateLogic::CheckForUpdates("5.0.0"); // TODO: Load from version.json
    if (!info.found) {
        SetWindowText(hStatusLabel, L"Application is up to date.");
        Sleep(2000);
        PostMessage(hwnd, WM_CLOSE, 0, 0);
        return;
    }

    SetWindowText(hStatusLabel, L"New update available!");
    EnableWindow(hUpdateButton, TRUE);

    // For now, let's auto-update if hidden or just wait for button?
    // The user's original C# code seemed to have a form that might have been hidden?
    // "if (fs::exists(updater)) spawn(updater, L"", true);" -> hidden
    
    // If hidden, we might want to just do it in the background if it's non-interactive
    // But usually an updater should show what it's doing.
    
    // Wait for button or just start? The C# code auto-started if I recall correctly.
    // Let's just start for now to keep it simple.
    
    std::string temp_zip = "update.zip";
    SetWindowText(hStatusLabel, L"Downloading update...");
    if (UpdateLogic::DownloadFile(info.download_url, temp_zip, [](float p) {
        SendMessage(hProgressBar, PBM_SETPOS, (WPARAM)(p * 100), 0);
    })) {
        SetWindowText(hStatusLabel, L"Extracting...");
        UpdateLogic::KillProcess(L"h5t.exe"); // New name for app
        UpdateLogic::KillProcess(L"Hammer5Tools.exe"); // Kill the launcher too
        
        // Extraction path should be root
        wchar_t buffer[MAX_PATH];
        GetModuleFileNameW(NULL, buffer, MAX_PATH);
        std::wstring root = std::filesystem::path(buffer).parent_path().wstring();
        std::string a_root(root.begin(), root.end()); // Simple conversion

        if (UpdateLogic::ExtractZip(temp_zip, a_root)) {
            SetWindowText(hStatusLabel, L"Update complete! Restarting...");
            DeleteFileA(temp_zip.c_str());
            Sleep(1000);
            
            // Restart the launcher
            std::wstring launcher_path = root + L"\\Hammer5Tools.exe";
            ShellExecuteW(NULL, L"open", launcher_path.c_str(), NULL, NULL, SW_SHOWNORMAL);
        } else {
            SetWindowText(hStatusLabel, L"Extraction failed.");
        }
    } else {
        SetWindowText(hStatusLabel, L"Download failed.");
    }
    
    Sleep(2000);
    PostMessage(hwnd, WM_CLOSE, 0, 0);
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int nCmdShow) {
    // Check if hidden
    bool hidden = (nCmdShow == SW_HIDE);

    INITCOMMONCONTROLSEX icex;
    icex.dwSize = sizeof(icex);
    icex.dwICC = ICC_PROGRESS_CLASS;
    InitCommonControlsEx(&icex);

    const wchar_t CLASS_NAME[] = L"Hammer5ToolsUpdaterWindow";
    WNDCLASS wc = {};
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);

    RegisterClass(&wc);

    hWndMain = CreateWindowEx(0, CLASS_NAME, L"Hammer 5 Tools - Updater",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU,
        CW_USEDEFAULT, CW_USEDEFAULT, 320, 180,
        NULL, NULL, hInstance, NULL);

    if (hWndMain == NULL) return 0;

    if (!hidden) {
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
