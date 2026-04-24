#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <filesystem>
#include <vector>
#include <fstream>
#include <shlobj.h>

#include "update_manager.h"

namespace fs = std::filesystem;

// Helper to convert wstring to utf8 string
std::string utf8_encode(const std::wstring& wstr) {
    if (wstr.empty()) return std::string();
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

static bool try_ipc(const std::string& json_msg) {
    HANDLE pipe = CreateFileA("\\\\.\\pipe\\Hammer5ToolsIPC",
        GENERIC_WRITE, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (pipe == INVALID_HANDLE_VALUE) return false;
    DWORD written;
    WriteFile(pipe, json_msg.c_str(), (DWORD)json_msg.size(), &written, NULL);
    CloseHandle(pipe);
    return true;
}

void SetRegistryKey(HKEY hKeyRoot, const std::wstring& subKey, const std::wstring& valueName, const std::wstring& data) {
    HKEY hKey;
    if (RegCreateKeyExW(hKeyRoot, subKey.c_str(), 0, NULL, REG_OPTION_NON_VOLATILE, KEY_WRITE, NULL, &hKey, NULL) == ERROR_SUCCESS) {
        if (valueName.empty()) {
            RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)data.c_str(), (DWORD)(data.size() + 1) * sizeof(wchar_t));
        } else {
            RegSetValueExW(hKey, valueName.c_str(), 0, REG_SZ, (const BYTE*)data.c_str(), (DWORD)(data.size() + 1) * sizeof(wchar_t));
        }
        RegCloseKey(hKey);
    }
}

void UnregisterAssociations() {
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickVMDL");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickVMDL");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickBatch");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickBatch");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickProcess");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickProcess");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\*\\shell\\Hammer5Tools_QuickProcess");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\editwith");
}

void RegisterAssociations(const std::wstring& exePath) {
    UnregisterAssociations();
    std::wstring openCmd = L"\"" + exePath + L"\" \"%1\"";
    std::wstring iconPath = exePath;
    std::wstring appIcon = iconPath + L",0";
    std::wstring vsmartIcon = iconPath + L",1";
    std::wstring consoleIcon = iconPath + L",2";
    std::wstring toolsIcon = iconPath + L",3";

    auto setIfEmptyOrUs = [&](const std::wstring& ext, const std::wstring& progID) {
        wchar_t current[256] = {0};
        DWORD size = sizeof(current);
        std::wstring key = L"Software\\Classes\\" + ext;
        HKEY hKey;
        bool shouldSet = true;
        if (RegOpenKeyExW(HKEY_CURRENT_USER, key.c_str(), 0, KEY_READ, &hKey) == ERROR_SUCCESS) {
            if (RegQueryValueExW(hKey, NULL, NULL, NULL, (BYTE*)current, &size) == ERROR_SUCCESS) {
                std::wstring val(current);
                if (!val.empty() && val != progID) shouldSet = false;
            }
            RegCloseKey(hKey);
        }
        if (shouldSet) SetRegistryKey(HKEY_CURRENT_USER, key, L"", progID);
    };

    setIfEmptyOrUs(L".vsmart", L"Hammer5Tools.SmartProp");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp", L"", L"SmartProp File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\DefaultIcon", L"", vsmartIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\open\\command", L"", openCmd);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\editwith", L"", L"Edit With Hammer5Tools");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\editwith", L"Icon", vsmartIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\editwith\\command", L"", openCmd);

    setIfEmptyOrUs(L".vsndevts", L"Hammer5Tools.SoundEvent");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent", L"", L"SoundEvent File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent\\DefaultIcon", L"", appIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent\\shell\\open\\command", L"", openCmd);

    setIfEmptyOrUs(L".hbat", L"Hammer5Tools.Batch");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch", L"", L"Hammer Batch File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch\\DefaultIcon", L"", consoleIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch\\shell\\open\\command", L"", openCmd);

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
}

static void spawn(const fs::path& exe, const std::wstring& args = L"", const fs::path& workingDir = L"", bool hidden = false, bool elevate = false) {
    SHELLEXECUTEINFOW sei = { sizeof(sei) };
    sei.fMask = SEE_MASK_NOCLOSEPROCESS;
    sei.lpFile = exe.c_str();
    sei.lpParameters = args.empty() ? NULL : args.c_str();
    sei.lpDirectory = workingDir.empty() ? NULL : workingDir.c_str();
    sei.nShow = hidden ? SW_HIDE : SW_SHOW;
    sei.lpVerb = elevate ? L"runas" : L"open";
    ShellExecuteExW(&sei);
}


int RunApp(int argc, wchar_t** argv) {
    std::string cmd = "show";
    std::string file_path;
    std::string editor_type = "smartprop";

    if (argc > 1) {
        std::wstring arg1 = argv[1];
        if (arg1 == L"--create-vmdl" && argc > 2) { cmd = "create_vmdl"; file_path = utf8_encode(argv[2]); }
        else if (arg1 == L"--quick-vmdl" && argc > 2) { cmd = "quick_vmdl"; file_path = utf8_encode(argv[2]); }
        else if (arg1 == L"--quick-vmdl-dir" && argc > 2) { cmd = "quick_vmdl"; file_path = utf8_encode(argv[2]); }
        else if (arg1 == L"--quick-batch" && argc > 2) { cmd = "quick_batch"; file_path = utf8_encode(argv[2]); }
        else if (arg1 == L"--quick-process" && argc > 2) { cmd = "quick_process"; file_path = utf8_encode(argv[2]); }
        else if (arg1 == L"--quick-process-file" && argc > 2) { cmd = "quick_process_file"; file_path = utf8_encode(argv[2]); }
        else if (arg1[0] != L'-') {
            cmd = "open_file";
            fs::path p(argv[1]);
            file_path = utf8_encode(fs::absolute(p).wstring());
            if (p.extension() == L".vsndevts") editor_type = "soundevent";
        }
    }

    std::string addon_hint;
    std::string marker_alt = "csgo_addons\\";
    auto pos = file_path.find(marker_alt);
    if (pos != std::string::npos) {
        auto start = pos + marker_alt.size();
        auto end = file_path.find('\\', start);
        if (end != std::string::npos) addon_hint = file_path.substr(start, end - start);
    }

    std::string msg = "{\"command\":\"" + cmd + "\"";
    if (!addon_hint.empty()) msg += ",\"addon_hint\":\"" + addon_hint + "\"";
    if (!file_path.empty()) {
        std::string escaped_path;
        for (char c : file_path) {
            if (c == '\\') escaped_path += "\\\\";
            else escaped_path += c;
        }
        msg += ",\"file_path\":\"" + escaped_path + "\"";
    }
    msg += ",\"editor_type\":\"" + editor_type + "\"}";

    if (try_ipc(msg)) {
        HWND hwnd = NULL;
        for (int i = 0; i < 20; i++) {
            hwnd = FindWindowW(NULL, L"Hammer 5 Tools");
            if (hwnd && IsWindowVisible(hwnd)) {
                if (IsIconic(hwnd)) ShowWindow(hwnd, SW_RESTORE);
                SetForegroundWindow(hwnd);
                break;
            }
            Sleep(50);
        }
        return 0;
    }

    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    fs::path base = fs::path(buffer).parent_path();
    RegisterAssociations(buffer);
    SetEnvironmentVariableW(L"HAMMER5TOOLS_ROOT", base.c_str());

    fs::path app_exe = base / "app" / "h5t.exe";
    spawn(app_exe, GetCommandLineW(), base);
    return 0;
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    int argc;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    
    std::wstring mode = L"launcher";
    fs::path srcDir, dstDir;
    int targetPid = 0;

    for (int i = 1; i < argc; i++) {
        if (wcscmp(argv[i], L"--mode") == 0 && i + 1 < argc) {
            mode = argv[++i];
        } else if (wcscmp(argv[i], L"--src") == 0 && i + 1 < argc) {
            srcDir = argv[++i];
        } else if (wcscmp(argv[i], L"--dst") == 0 && i + 1 < argc) {
            dstDir = argv[++i];
        } else if (wcscmp(argv[i], L"--pid") == 0 && i + 1 < argc) {
            targetPid = _wtoi(argv[++i]);
        }
    }

    if (mode == L"replace") {
        UpdateManager::RunReplaceMode(targetPid, srcDir, dstDir);
        LocalFree(argv);
        return 0;
    } else if (mode == L"cleanup") {
        wchar_t buffer[MAX_PATH];
        GetModuleFileNameW(NULL, buffer, MAX_PATH);
        UpdateManager::RunCleanupMode(fs::path(buffer).parent_path());
        // After cleanup, proceed to launcher/app
    }

    // Launcher / App mode
    HANDLE hMutex = CreateMutexW(NULL, TRUE, L"Global\\Hammer5Tools_LauncherMutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        // Just try to forward to existing instance
        RunApp(argc, argv);
        LocalFree(argv);
        return 0;
    }

    if (mode == L"launcher" || mode == L"cleanup") {
        BuildInfo local = UpdateManager::GetLocalBuildInfo();
        ReleaseInfo rel = UpdateManager::CheckForUpdates(local);

        if (rel.found && !rel.download_url.empty()) {
            // Update available!
            fs::path staging = fs::path(getenv("LOCALAPPDATA")) / "Hammer5Tools" / "staging";
            fs::create_directories(staging);
            fs::path zipFile = staging / "update.zip";

            if (UpdateManager::DownloadFile(rel.download_url, zipFile)) {
                if (UpdateManager::ExtractZip(zipFile, staging)) {
                    // Prepare replacer
                    wchar_t selfPath[MAX_PATH];
                    GetModuleFileNameW(NULL, selfPath, MAX_PATH);
                    fs::path tempReplacer = fs::path(getenv("TEMP")) / "h5t_replacer.exe";
                    fs::copy_file(selfPath, tempReplacer, fs::copy_options::overwrite_existing);

                    wchar_t argsStr[1024];
                    swprintf_s(argsStr, 1024, L"--mode replace --pid %d --src \"%ls\" --dst \"%ls\"", 
                             GetCurrentProcessId(), staging.c_str(), fs::path(selfPath).parent_path().c_str());
                    
                    // Check if we need elevation to write to destination
                    bool needsElevation = false;
                    fs::path testFile = fs::path(selfPath).parent_path() / ".write_test";
                    std::ofstream ofs(testFile);
                    if (!ofs.is_open()) {
                        needsElevation = true;
                    } else {
                        ofs.close();
                        fs::remove(testFile);
                    }

                    spawn(tempReplacer, std::wstring(argsStr), fs::path(L""), false, needsElevation);


                    LocalFree(argv);
                    return 0;
                }
            }
        }
    }

    // Start App
    RunApp(argc, argv);

    if (hMutex) ReleaseMutex(hMutex);
    LocalFree(argv);
    return 0;
}
