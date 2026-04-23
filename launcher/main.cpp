#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <filesystem>
#include <vector>

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
    
    // Launcher sets HAMMER5TOOLS_ROOT for the python app
    SetEnvironmentVariableW(L"HAMMER5TOOLS_ROOT", base.c_str());

    // Python app is now app/h5t.exe
    fs::path app_exe = base / "app" / "h5t.exe";
    spawn(app_exe, GetCommandLineW());

    fs::path updater = base / "Hammer5ToolsUpdater.exe";
    if (fs::exists(updater)) {
        spawn(updater, L"", true); // Run updater hidden
    }

    LocalFree(argv);
    return 0;
}
