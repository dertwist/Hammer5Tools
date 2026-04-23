#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <commctrl.h>
#include <string>
#include <thread>
#include <filesystem>
#include <fstream>
#include <atomic>
#include "update_logic.h"

#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "shell32.lib")

// Window controls
HWND hWndMain;
HWND hProgressBar;
HWND hStatusLabel;
HWND hChangelogEdit;
HWND hUpdateButton;
HWND hCancelButton;

// Version is now read from app/version.txt at runtime

std::atomic<bool> g_startUpdate(false);
bool g_isSilent = false;
bool g_isInteractive = false;

LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam,
                            LPARAM lParam) {
  switch (uMsg) {
  case WM_CREATE: {
    hStatusLabel = CreateWindowEx(0, L"STATIC", L"Checking for updates...",
                                  WS_CHILD | WS_VISIBLE | SS_CENTER, 10, 10,
                                  360, 20, hwnd, NULL, NULL, NULL);

    hChangelogEdit =
        CreateWindowEx(WS_EX_CLIENTEDGE, L"EDIT", L"",
                       WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE |
                           ES_AUTOVSCROLL | ES_READONLY,
                       10, 40, 360, 300, hwnd, NULL, NULL, NULL);

    hProgressBar = CreateWindowEx(0, PROGRESS_CLASS, NULL,
                                  WS_CHILD | WS_VISIBLE | PBS_SMOOTH, 10, 350,
                                  360, 25, hwnd, NULL, NULL, NULL);

    hUpdateButton = CreateWindowEx(0, L"BUTTON", L"Update Now",
                                   WS_CHILD | WS_VISIBLE | WS_DISABLED, 60, 390,
                                   120, 30, hwnd, (HMENU)1, NULL, NULL);

    hCancelButton =
        CreateWindowEx(0, L"BUTTON", L"Cancel", WS_CHILD | WS_VISIBLE, 200, 390,
                       120, 30, hwnd, (HMENU)2, NULL, NULL);

    return 0;
  }
  case WM_COMMAND:
    if (LOWORD(wParam) == 1) { // Update button
      EnableWindow(hUpdateButton, FALSE);
      EnableWindow(hCancelButton, FALSE);
      g_startUpdate = true;
    } else if (LOWORD(wParam) == 2) { // Cancel button
      PostQuitMessage(0);
    }
    break;
  case WM_DESTROY:
    PostQuitMessage(0);
    return 0;
  }
  return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

std::string GetCurrentVersion() {
    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    std::filesystem::path root = std::filesystem::path(buffer).parent_path();
    std::filesystem::path version_file = root / "app" / "version.txt";
    
    std::ifstream file(version_file);
    if (file.is_open()) {
        std::string version;
        file >> version;
        if (!version.empty()) return version;
    }
    return "5.0.0"; // Fallback
}

void UpdateThread(HWND hwnd) {
  std::string current_version = GetCurrentVersion();
  
  // 1. Check version
  ReleaseInfo info = UpdateLogic::CheckForUpdates(current_version);

  if (!info.found) {
    if (g_isInteractive) {
      SetWindowText(hStatusLabel, L"Application is up to date.");
      Sleep(2000);
    }
    PostMessage(hwnd, WM_CLOSE, 0, 0);
    return;
  }

  // Found update
  if (g_isSilent) {
    ShowWindow(hwnd, SW_SHOWNORMAL);
    SetForegroundWindow(hwnd);
  }

  std::wstring status = L"New version available: " +
                        std::wstring(info.version.begin(), info.version.end());
  if (info.is_prerelease) {
    if (!info.publish_date.empty()) {
      std::string date = info.publish_date;
      if (date.length() >= 10)
        date = date.substr(0, 10); // YYYY-MM-DD
      status += L" (" + std::wstring(date.begin(), date.end()) + L")";
    }
    if (!info.commit_sha.empty()) {
      status += L" [" +
                std::wstring(info.commit_sha.begin(), info.commit_sha.end()) +
                L"]";
    }
  }
  SetWindowText(hStatusLabel, status.c_str());

  std::wstring changelog =
      std::wstring(info.changelog.begin(), info.changelog.end());
  SetWindowText(hChangelogEdit, changelog.c_str());

  EnableWindow(hUpdateButton, TRUE);

  // Wait for user confirmation
  while (!g_startUpdate) {
    Sleep(100);
    // Check if window was closed
    if (!IsWindow(hwnd))
      return;
  }

  // Proceed with update
  std::string temp_zip = "update.zip";
  SetWindowText(hStatusLabel, L"Downloading update...");
  if (UpdateLogic::DownloadFile(info.download_url, temp_zip, [](float p) {
        SendMessage(hProgressBar, PBM_SETPOS, (WPARAM)(p * 100), 0);
      })) {
    SetWindowText(hStatusLabel, L"Extracting...");
    UpdateLogic::KillProcess(L"h5t.exe");
    UpdateLogic::KillProcess(L"Hammer5Tools.exe");

    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    std::wstring root = std::filesystem::path(buffer).parent_path().wstring();
    std::string a_root(root.begin(), root.end());

    if (UpdateLogic::ExtractZip(temp_zip, a_root)) {
      SetWindowText(hStatusLabel, L"Update complete! Restarting...");
      DeleteFileA(temp_zip.c_str());
      Sleep(1000);

      std::wstring launcher_path = root + L"\\Hammer5Tools.exe";
      ShellExecuteW(NULL, L"open", launcher_path.c_str(), NULL, NULL,
                    SW_SHOWNORMAL);
    } else {
      SetWindowText(hStatusLabel, L"Extraction failed.");
      Sleep(2000);
    }
  } else {
    SetWindowText(hStatusLabel, L"Download failed.");
    Sleep(2000);
  }

  PostMessage(hwnd, WM_CLOSE, 0, 0);
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR lpCmdLine,
                   int nCmdShow) {
  std::string cmdLine = lpCmdLine;
  if (cmdLine.find("--silent") != std::string::npos)
    g_isSilent = true;
  if (cmdLine.find("--interactive") != std::string::npos)
    g_isInteractive = true;

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

  hWndMain =
      CreateWindowEx(0, CLASS_NAME, L"Hammer 5 Tools - Updater",
                     WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU, CW_USEDEFAULT,
                     CW_USEDEFAULT, 400, 480, NULL, NULL, hInstance, NULL);

  if (hWndMain == NULL)
    return 0;

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
