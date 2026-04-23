#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <filesystem>
#include <vector>
#include <shlobj.h>

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
            RegSetValueExW(hKey, NULL, 0, REG_SZ, (const BYTE*)data.c_str(), (data.size() + 1) * sizeof(wchar_t));
        } else {
            RegSetValueExW(hKey, valueName.c_str(), 0, REG_SZ, (const BYTE*)data.c_str(), (data.size() + 1) * sizeof(wchar_t));
        }
        RegCloseKey(hKey);
    }
}

void UnregisterAssociations() {
    // Clean up old/stale registry entries
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickVMDL");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickVMDL");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickBatch");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickBatch");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickProcess");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickProcess");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\*\\shell\\Hammer5Tools_QuickProcess");
}

void RegisterAssociations(const std::wstring& exePath) {
    UnregisterAssociations();

    std::wstring openCmd = L"\"" + exePath + L"\" \"%1\"";
    std::wstring iconPath = exePath;
    
    // Icon indices (0-based) matching resources.rc
    std::wstring appIcon = iconPath + L",0";
    std::wstring vmdlIcon = iconPath + L",1";
    std::wstring batchIcon = iconPath + L",2";
    std::wstring processIcon = iconPath + L",3";

    // Helper to set extension if empty or already set to us
    auto setIfEmptyOrUs = [&](const std::wstring& ext, const std::wstring& progID) {
        wchar_t current[256] = {0};
        DWORD size = sizeof(current);
        std::wstring key = L"Software\\Classes\\" + ext;
        HKEY hKey;
        bool shouldSet = true;
        if (RegOpenKeyExW(HKEY_CURRENT_USER, key.c_str(), 0, KEY_READ, &hKey) == ERROR_SUCCESS) {
            if (RegQueryValueExW(hKey, NULL, NULL, NULL, (BYTE*)current, &size) == ERROR_SUCCESS) {
                std::wstring val(current);
                if (!val.empty() && val != progID) {
                    shouldSet = false; // Already set to something else
                }
            }
            RegCloseKey(hKey);
        }
        if (shouldSet) {
            SetRegistryKey(HKEY_CURRENT_USER, key, L"", progID);
        }
    };

    // .vsmart
    setIfEmptyOrUs(L".vsmart", L"Hammer5Tools.SmartProp");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp", L"", L"SmartProp File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\DefaultIcon", L"", vmdlIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\open\\command", L"", openCmd);

    // .vsndevts
    setIfEmptyOrUs(L".vsndevts", L"Hammer5Tools.SoundEvent");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent", L"", L"SoundEvent File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent\\DefaultIcon", L"", appIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent\\shell\\open\\command", L"", openCmd);

    // .hbat (Hammer Batch)
    setIfEmptyOrUs(L".hbat", L"Hammer5Tools.Batch");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch", L"", L"Hammer Batch File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch\\DefaultIcon", L"", batchIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch\\shell\\open\\command", L"", openCmd);

    // Folder context menu entries
    std::wstring quickVmdlDirCmd = L"\"" + exePath + L"\" --quick-vmdl-dir \"%1\"";
    std::wstring batchDirCmd = L"\"" + exePath + L"\" --quick-batch \"%1\"";
    std::wstring processDirCmd = L"\"" + exePath + L"\" --quick-process \"%1\"";

    auto addContextEntry = [&](const std::wstring& root, const std::wstring& title, const std::wstring& icon, const std::wstring& cmd) {
        SetRegistryKey(HKEY_CURRENT_USER, root, L"", title);
        SetRegistryKey(HKEY_CURRENT_USER, root, L"Icon", icon);
        SetRegistryKey(HKEY_CURRENT_USER, root + L"\\command", L"", cmd);
    };

    // Directory
    addContextEntry(L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickVMDL", L"Quick Create VMDL", vmdlIcon, quickVmdlDirCmd);
    addContextEntry(L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickBatch", L"Quick Create Batch", batchIcon, batchDirCmd);
    addContextEntry(L"Software\\Classes\\Directory\\shell\\Hammer5Tools_QuickProcess", L"Quick Process folder", processIcon, processDirCmd);

    // Directory Background (right click inside folder)
    addContextEntry(L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickVMDL", L"Quick Create VMDL", vmdlIcon, L"\"" + exePath + L"\" --quick-vmdl-dir \"%V\"");
    addContextEntry(L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickBatch", L"Quick Create Batch", batchIcon, L"\"" + exePath + L"\" --quick-batch \"%V\"");
    addContextEntry(L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_QuickProcess", L"Quick Process folder", processIcon, L"\"" + exePath + L"\" --quick-process \"%V\"");

    // Quick Create VMDL (Specific to .fbx and .obj)
    std::wstring quickVmdlCmd = L"\"" + exePath + L"\" --quick-vmdl \"%1\"";
    std::vector<std::wstring> meshExts = { L".fbx", L".obj" };
    for (const auto& ext : meshExts) {
        std::wstring root = L"Software\\Classes\\SystemFileAssociations\\" + ext + L"\\shell\\Hammer5Tools_QuickVMDL";
        addContextEntry(root, L"Quick Create VMDL", vmdlIcon, quickVmdlCmd);
    }

    // Quick Create Batch (Specific to .vmdl)
    std::wstring batchCmd = L"\"" + exePath + L"\" --quick-batch \"%1\"";
    std::wstring vmdlBatchRoot = L"Software\\Classes\\SystemFileAssociations\\.vmdl\\shell\\Hammer5Tools_QuickBatch";
    addContextEntry(vmdlBatchRoot, L"Quick Create Batch", batchIcon, batchCmd);

    // Quick Process File
    std::wstring processFileCmd = L"\"" + exePath + L"\" --quick-process-file \"%1\"";
    
    // Add "Quick Process file" to specific asset types
    std::vector<std::wstring> processExts = { L".vmdl", L".vmat" };
    for (const auto& ext : processExts) {
        std::wstring root = L"Software\\Classes\\SystemFileAssociations\\" + ext + L"\\shell\\Hammer5Tools_QuickProcess";
        addContextEntry(root, L"Quick Process file", processIcon, processFileCmd);
    }

    // Add "Quick Process file" to our own ProgIDs
    auto addProcessToProgID = [&](const std::wstring& progID) {
        std::wstring root = L"Software\\Classes\\" + progID + L"\\shell\\Hammer5Tools_QuickProcess";
        addContextEntry(root, L"Quick Process file", processIcon, processFileCmd);
    };
    addProcessToProgID(L"Hammer5Tools.SmartProp");
    addProcessToProgID(L"Hammer5Tools.SoundEvent");

    // Add "Process batch file" specifically for .hbat
    addContextEntry(L"Software\\Classes\\Hammer5Tools.Batch\\shell\\Hammer5Tools_ProcessBatch", L"Process batch file", processIcon, processFileCmd);

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
}

static void spawn(const fs::path& exe, const std::wstring& args = L"", bool hidden = false) {
    SHELLEXECUTEINFOW sei = { sizeof(sei) };
    sei.fMask = SEE_MASK_NOCLOSEPROCESS;
    sei.lpFile = exe.c_str();
    sei.lpParameters = args.empty() ? NULL : args.c_str();
    sei.nShow = hidden ? SW_HIDE : SW_SHOW;
    ShellExecuteExW(&sei);
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    std::string cmd = "show";
    std::string file_path;
    std::string editor_type = "smartprop";

    int argc;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    
    // Simple arg parsing logic mirroring original C#
    if (argc > 1) {
        std::wstring arg1 = argv[1];
        if (arg1 == L"--create-vmdl" && argc > 2) {
            cmd = "create_vmdl";
            file_path = utf8_encode(argv[2]);
        } else if (arg1 == L"--quick-vmdl" && argc > 2) {
            cmd = "quick_vmdl";
            file_path = utf8_encode(argv[2]);
        } else if (arg1 == L"--quick-vmdl-dir" && argc > 2) {
            cmd = "quick_vmdl";
            file_path = utf8_encode(argv[2]);
        } else if (arg1 == L"--quick-batch" && argc > 2) {
            cmd = "quick_batch";
            file_path = utf8_encode(argv[2]);
        } else if (arg1 == L"--quick-process" && argc > 2) {
            cmd = "quick_process";
            file_path = utf8_encode(argv[2]);
        } else if (arg1 == L"--quick-process-file" && argc > 2) {
            cmd = "quick_process_file";
            file_path = utf8_encode(argv[2]);
        } else if (arg1[0] != L'-') {
            cmd = "open_file";
            fs::path p(argv[1]);
            file_path = utf8_encode(fs::absolute(p).wstring());
            if (p.extension() == L".vsndevts") {
                editor_type = "soundevent";
            }
        }
    }

    // Extract addon name from path like: ...\csgo_addons\<addon_name>\...
    std::string addon_hint;
    std::string marker = "csgo_addons\\\\"; // Escaped backslash for UTF-8 comparison if needed, but file_path uses \\ from utf8_encode(wstring)
    // Wait, utf8_encode just converts wstring to string. On Windows, wstring uses \.
    std::string marker_alt = "csgo_addons\\";
    auto pos = file_path.find(marker_alt);
    if (pos != std::string::npos) {
        auto start = pos + marker_alt.size();
        auto end = file_path.find('\\', start);
        if (end != std::string::npos)
            addon_hint = file_path.substr(start, end - start);
    }

    // Build JSON manually
    std::string msg = "{\"command\":\"" + cmd + "\"";
    if (!addon_hint.empty()) {
        msg += ",\"addon_hint\":\"" + addon_hint + "\"";
    }
    if (!file_path.empty()) {
        // Simple JSON escaping for backslashes
        std::string escaped_path;
        for (char c : file_path) {
            if (c == '\\') escaped_path += "\\\\";
            else escaped_path += c;
        }
        msg += ",\"file_path\":\"" + escaped_path + "\"";
    }
    msg += ",\"editor_type\":\"" + editor_type + "\"}";

    if (try_ipc(msg)) {
        // Force the existing window to the front. 
        // We retry a few times to give the app time to process the IPC message and show the window.
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
        LocalFree(argv);
        return 0;
    }

    // No running instance — launch app + updater
    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    fs::path base = fs::path(buffer).parent_path();
    
    // Register file associations and context menu
    RegisterAssociations(buffer);
    
    // Launcher sets HAMMER5TOOLS_ROOT for the python app
    SetEnvironmentVariableW(L"HAMMER5TOOLS_ROOT", base.c_str());

    // Python app is now app/h5t.exe
    fs::path app_exe = base / "app" / "h5t.exe";
    spawn(app_exe, GetCommandLineW());

    fs::path updater = base / "Hammer5ToolsUpdater.exe";
    if (fs::exists(updater)) {
        spawn(updater, L"--silent", true); // Run updater hidden
    }

    LocalFree(argv);
    return 0;
}
