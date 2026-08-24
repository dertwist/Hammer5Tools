#include "request.hpp"

#include <windows.h>

#include <cassert>
#include <chrono>
#include <string>

namespace
{
void TestProcessForwarding(const wchar_t* launcherPath)
{
    const auto suffix = std::to_wstring(GetCurrentProcessId());
    const auto pipeName = L"\\\\.\\pipe\\Hammer5ToolsLauncherTest." + suffix;
    const auto mutexName = L"Local\\Hammer5ToolsLauncherTest." + suffix;
    SetEnvironmentVariableW(L"H5T_IPC_PIPE", pipeName.c_str());
    SetEnvironmentVariableW(L"H5T_INSTANCE_MUTEX", mutexName.c_str());
    const auto pipe = CreateNamedPipeW(pipeName.c_str(), PIPE_ACCESS_INBOUND,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT, 1, 4096, 4096, 5000, nullptr);
    assert(pipe != INVALID_HANDLE_VALUE);

    std::wstring command = L"\"" + std::wstring(launcherPath)
        + L"\" --quick-process-file \"C:\\maps with spaces\\test.vmap\"";
    std::vector<wchar_t> mutableCommand(command.begin(), command.end());
    mutableCommand.push_back(L'\0');
    STARTUPINFOW startup{sizeof(startup)};
    PROCESS_INFORMATION process{};
    assert(CreateProcessW(launcherPath, mutableCommand.data(), nullptr, nullptr, FALSE, 0,
                          nullptr, nullptr, &startup, &process));
    assert(ConnectNamedPipe(pipe, nullptr) || GetLastError() == ERROR_PIPE_CONNECTED);
    std::string message(4096, '\0');
    DWORD read = 0;
    assert(ReadFile(pipe, message.data(), static_cast<DWORD>(message.size()), &read, nullptr));
    message.resize(read);
    assert(message.find("\"protocol_version\":1") != std::string::npos);
    assert(message.find("quick_process_file") != std::string::npos);
    assert(message.find("maps with spaces") != std::string::npos);
    assert(WaitForSingleObject(process.hProcess, 5000) == WAIT_OBJECT_0);
    DWORD exitCode = 1;
    GetExitCodeProcess(process.hProcess, &exitCode);
    assert(exitCode == 0);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    CloseHandle(pipe);
}
}

int wmain(int argc, wchar_t** argv)
{
    assert(launcher::QuoteArgument(L"plain") == L"plain");
    assert(launcher::QuoteArgument(L"two words") == L"\"two words\"");
    const auto request = launcher::ParseRequest({L"--quick-vmdl", L"folder with spaces"}, L"C:\\work");
    assert(request.Command == "quick_vmdl");
    assert(request.FilePath == L"C:\\work\\folder with spaces");
    const auto json = launcher::SerializeRequest(request);
    assert(json.find("\"protocol_version\":1") != std::string::npos);
    assert(json.find("folder with spaces") != std::string::npos);
    const auto openRequest = launcher::ParseRequest({L"events\\addon.vsndevts"}, L"C:\\work");
    assert(openRequest.Command == "open_file");
    assert(openRequest.EditorType == "soundevent");
    assert(openRequest.FilePath == L"C:\\work\\events\\addon.vsndevts");
    assert(argc == 2);
    TestProcessForwarding(argv[1]);
    return 0;
}
