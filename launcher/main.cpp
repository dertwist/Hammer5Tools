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

void RegisterAssociations(const std::wstring& exePath) {
    std::wstring openCmd = L"\"" + exePath + L"\" \"%1\"";
    std::wstring iconCmd = L"\"" + exePath + L"\",0";
    std::wstring smartPropIconCmd = L"\"" + exePath + L"\",1";

    // .vsmart
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\.vsmart", L"", L"Hammer5Tools.SmartProp");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp", L"", L"SmartProp File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\DefaultIcon", L"", smartPropIconCmd);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SmartProp\\shell\\open\\command", L"", openCmd);

    // .vsndevts
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\.vsndevts", L"", L"Hammer5Tools.SoundEvent");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent", L"", L"SoundEvent File");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent\\DefaultIcon", L"", iconCmd);
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Hammer5Tools.SoundEvent\\shell\\open\\command", L"", openCmd);

    // Directory context menu (right click on folder)
    std::wstring vmdlCmd = L"\"" + exePath + L"\" --create-vmdl \"%V\"";
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_VMDL", L"", L"Create VMDL");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_VMDL\\command", L"", vmdlCmd);

    std::wstring vmatCmd = L"\"" + exePath + L"\" --create-vmat \"%V\"";
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_VMAT", L"", L"Create VMAT");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\shell\\Hammer5Tools_VMAT\\command", L"", vmatCmd);

    // Directory background context menu (right click inside folder)
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_VMDL", L"", L"Create VMDL");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_VMDL\\command", L"", vmdlCmd);

    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_VMAT", L"", L"Create VMAT");
    SetRegistryKey(HKEY_CURRENT_USER, L"Software\\Classes\\Directory\\Background\\shell\\Hammer5Tools_VMAT\\command", L"", vmatCmd);

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
        } else if (arg1 == L"--create-vmat" && argc > 2) {
            cmd = "create_vmat";
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

    // Build JSON manually
    std::string msg = "{\"command\":\"" + cmd + "\"";
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
