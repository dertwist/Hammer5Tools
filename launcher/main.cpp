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
        // Handle Velopack hooks by exiting immediately. 
        // Logic moved to main application.
        if (wcscmp(argv[i], L"--squirrel-install") == 0 || 
            wcscmp(argv[i], L"--squirrel-updated") == 0 ||
            wcscmp(argv[i], L"--squirrel-uninstall") == 0 || 
            wcscmp(argv[i], L"--squirrel-obsoleted") == 0) {
            LocalFree(argv);
            return 0;
        }

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

    // Attempt IPC to existing instance
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

    // No existing instance, spawn the main app
    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    fs::path base = fs::path(buffer).parent_path();
    fs::path app_exe = base / "Hammer5Tools.exe";

    if (fs::exists(app_exe)) {
        spawn(app_exe, GetCommandLineW(), base);
    }

    LocalFree(argv);
    return 0;
}
