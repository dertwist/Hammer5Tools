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
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch\\DefaultIcon", L"", appIcon);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.Batch\\shell\\open\\command", L"", openCmd);

    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL);
}

void spawn(const fs::path& exe, const std::wstring& args, const fs::path& cwd) {
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    std::wstring cmd = L"\"" + exe.wstring() + L"\" " + args;
    std::vector<wchar_t> cmdBuf(cmd.begin(), cmd.end());
    cmdBuf.push_back(0);

    if (CreateProcessW(NULL, cmdBuf.data(), NULL, NULL, FALSE, 0, NULL, 
                      cwd.empty() ? NULL : cwd.c_str(), &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) {
    int argc;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    
    std::wstring filePath;
    std::string command = "show";
    std::string editor_type = "smartprop";

    for (int i = 1; i < argc; i++) {
        if (wcscmp(argv[i], L"--create-vmdl") == 0 && i + 1 < argc) {
            command = "create_vmdl";
            filePath = argv[++i];
        } else if (wcscmp(argv[i], L"--quick-vmdl") == 0 && i + 1 < argc) {
            command = "quick_vmdl";
            filePath = argv[++i];
        } else if (wcscmp(argv[i], L"--quick-batch") == 0 && i + 1 < argc) {
            command = "quick_batch";
            filePath = argv[++i];
        } else if (wcscmp(argv[i], L"--quick-process") == 0 && i + 1 < argc) {
            command = "quick_process";
            filePath = argv[++i];
        } else {
            filePath = argv[i];
            command = "open_file";
            fs::path p(filePath);
            if (p.extension() == ".vsndevts") editor_type = "soundevent";
        }
    }

    std::string msg = "{\"command\":\"" + command + "\"";
    if (!filePath.empty()) {
        std::string utf8_path = utf8_encode(filePath);
        std::string escaped_path;
        for (char c : utf8_path) {
            if (c == '\\') escaped_path += "\\\\";
            else escaped_path += c;
        }
        msg += ",\"file_path\":\"" + escaped_path + "\"";
    }
    msg += ",\"editor_type\":\"" + editor_type + "\"}";

    if (try_ipc(msg)) {
        LocalFree(argv);
        return 0;
    }

    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    fs::path base = fs::path(buffer).parent_path();
    
    // Auto-register on launch if needed
    RegisterAssociations(buffer);

    fs::path app_exe = base / "Hammer5Tools.exe";
    if (fs::exists(app_exe)) {
        spawn(app_exe, GetCommandLineW(), base);
    }

    LocalFree(argv);
    return 0;
}
