#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <filesystem>
#include <vector>
#include <shlobj.h>
#include <fstream>
#include <chrono>

namespace fs = std::filesystem;

// Helper to convert wstring to utf8 string
std::string utf8_encode(const std::wstring& wstr) {
    if (wstr.empty()) return std::string();
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &wstr[0], (int)wstr.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

static void log_hook(const fs::path& log_dir, const std::wstring& msg) {
    try {
        fs::create_directories(log_dir);
        std::ofstream log_file(log_dir / "hook.log", std::ios::app);
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        char time_str[26];
        ctime_s(time_str, sizeof(time_str), &time);
        log_file << time_str << " [Launcher] " << utf8_encode(msg) << "\n";
    } catch (...) {}
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
    
    // 1. Check for Velopack hooks IMMEDIATELY and handle them NATIVELY (no Python launch)
    bool is_install_hook = false;
    bool is_uninstall_hook = false;

    for (int i = 1; i < argc; i++) {
        std::wstring arg = argv[i];
        if (arg == L"--velopack-install" || arg == L"--velopack-updated" || 
            arg == L"--squirrel-install" || arg == L"--squirrel-updated") {
            is_install_hook = true;
        }
        else if (arg == L"--velopack-uninstall" || arg == L"--velopack-obsolete" || arg == L"--velopack-obsoleted" ||
                 arg == L"--squirrel-uninstall" || arg == L"--squirrel-obsolete" || arg == L"--squirrel-obsoleted") {
            is_uninstall_hook = true;
        }
    }

    if (is_install_hook || is_uninstall_hook) {
        wchar_t buf[MAX_PATH];
        GetModuleFileNameW(NULL, buf, MAX_PATH);
        fs::path exe_path(buf);
        fs::path install_root = exe_path.parent_path().parent_path();
        fs::path userdata_path = install_root / "userdata";

        wchar_t appdata[MAX_PATH];
        SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, appdata);
        fs::path backup_root = fs::path(appdata) / "Hammer5Tools.Backup";
        fs::path backup_userdata = backup_root / "userdata";
        fs::path backup_sentinel = backup_root / "USERDATA_BACKUP_VALID";

        if (is_uninstall_hook) {
            log_hook(backup_root, L"Uninstall hook detected - backing up userdata");
            if (fs::exists(userdata_path) && fs::is_directory(userdata_path)) {
                try {
                    fs::create_directories(backup_root);
                    if (fs::exists(backup_userdata)) fs::remove_all(backup_userdata);
                    fs::copy(userdata_path, backup_userdata, fs::copy_options::recursive);
                    
                    std::ofstream(backup_sentinel) << "valid";
                    log_hook(backup_root, L"Backup completed successfully");
                } catch (const std::exception& e) {
                    log_hook(backup_root, L"BACKUP FAILED: " + std::wstring(e.what(), e.what() + strlen(e.what())));
                }
            }
        }

        if (is_install_hook) {
            log_hook(backup_root, L"Install hook detected - restoring userdata");
            if (fs::exists(backup_userdata) && fs::exists(backup_sentinel)) {
                try {
                    fs::create_directories(userdata_path.parent_path());
                    if (fs::exists(userdata_path)) fs::remove_all(userdata_path);
                    fs::copy(backup_userdata, userdata_path, fs::copy_options::recursive);
                    
                    fs::remove_all(backup_userdata);
                    fs::remove(backup_sentinel);
                    log_hook(backup_root, L"Restore completed successfully");
                } catch (const std::exception& e) {
                    log_hook(backup_root, L"RESTORE FAILED: " + std::wstring(e.what(), e.what() + strlen(e.what())));
                }
            }
        }

        LocalFree(argv);
        return 0; // EXIT IMMEDIATELY - never start Python for hooks
    }

    // 2. Normal execution logic (IPC and spawning Python)
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
        } else if (wcscmp(argv[i], L"--quick-process-file") == 0 && i + 1 < argc) {
            command = "quick_process_file";
            filePath = argv[++i];
        } else if (argv[i][0] != L'-') {
            command = "open_file";
            filePath = argv[i];
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

    // No existing instance, spawn the main app (Python)
    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    fs::path base = fs::path(buffer).parent_path();
    fs::path app_exe = base / "Hammer5Tools_Core.exe"; // Launch the internal core

    if (fs::exists(app_exe)) {
        spawn(app_exe, GetCommandLineW(), base);
    } else {
        // Fallback for dev environment
        app_exe = base / "Hammer5Tools.exe";
        if (fs::exists(app_exe)) spawn(app_exe, GetCommandLineW(), base);
    }

    LocalFree(argv);
    return 0;
}
