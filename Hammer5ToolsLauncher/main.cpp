#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>

#include "request.hpp"

#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace
{
constexpr auto DefaultPipeName = L"\\\\.\\pipe\\Hammer5ToolsIPC";
constexpr auto DefaultMutexName = L"Local\\Hammer5Tools.Launcher.Instance.v1";
constexpr DWORD RestartExitCode = 75;

std::wstring EnvironmentOrDefault(const wchar_t* name, const wchar_t* fallback)
{
    const auto size = GetEnvironmentVariableW(name, nullptr, 0);
    if (size == 0)
        return fallback;
    std::wstring value(size, L'\0');
    GetEnvironmentVariableW(name, value.data(), size);
    value.resize(size - 1);
    return value;
}

const std::wstring& PipeName()
{
    static const auto value = EnvironmentOrDefault(L"H5T_IPC_PIPE", DefaultPipeName);
    return value;
}

const std::wstring& MutexName()
{
    static const auto value = EnvironmentOrDefault(L"H5T_INSTANCE_MUTEX", DefaultMutexName);
    return value;
}

fs::path ExecutablePath()
{
    std::wstring buffer(32768, L'\0');
    const auto length = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    buffer.resize(length);
    return buffer;
}

void Log(const fs::path& directory, const std::wstring& message)
{
    try
    {
        fs::create_directories(directory);
        std::wofstream stream(directory / "launcher.log", std::ios::app);
        stream << message << L'\n';
    }
    catch (...) {}
}

LRESULT CALLBACK ErrorDialogProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_SIZE:
    {
        RECT client{};
        GetClientRect(hwnd, &client);
        constexpr auto buttonHeight = 28;
        constexpr auto padding = 8;
        if (const auto edit = GetDlgItem(hwnd, 1))
            MoveWindow(edit, padding, padding, client.right - padding * 2,
                       client.bottom - buttonHeight - padding * 3, TRUE);
        if (const auto button = GetDlgItem(hwnd, IDOK))
            MoveWindow(button, client.right - 90 - padding, client.bottom - buttonHeight - padding,
                       90, buttonHeight, TRUE);
        return 0;
    }
    case WM_COMMAND:
        if (LOWORD(wParam) == IDOK || LOWORD(wParam) == IDCANCEL)
            DestroyWindow(hwnd);
        return 0;
    case WM_CLOSE:
        DestroyWindow(hwnd);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcW(hwnd, message, wParam, lParam);
    }
}

// A read-only multiline EDIT control natively supports mouse/keyboard
// selection, Ctrl+C, and a right-click Copy menu, so this is preferred
// over MessageBoxW for text the user may want to copy (crash details,
// log paths).
void ShowErrorDialog(const std::wstring& message, const std::wstring& title, LPCWSTR icon = IDI_ERROR)
{
    const auto instance = GetModuleHandleW(nullptr);
    static const auto registered = [instance] {
        WNDCLASSW windowClass{};
        windowClass.lpfnWndProc = ErrorDialogProc;
        windowClass.hInstance = instance;
        windowClass.lpszClassName = L"Hammer5ToolsErrorDialog";
        windowClass.hCursor = LoadCursorW(nullptr, IDC_ARROW);
        windowClass.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_BTNFACE + 1);
        windowClass.hIcon = LoadIconW(nullptr, IDI_ERROR);
        return RegisterClassW(&windowClass) != 0;
    }();
    (void)registered;

    constexpr auto width = 640;
    constexpr auto height = 420;
    const auto hwnd = CreateWindowExW(
        WS_EX_DLGMODALFRAME, L"Hammer5ToolsErrorDialog", title.c_str(),
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_VISIBLE,
        (GetSystemMetrics(SM_CXSCREEN) - width) / 2, (GetSystemMetrics(SM_CYSCREEN) - height) / 2,
        width, height, nullptr, nullptr, instance, nullptr);
    if (hwnd == nullptr)
    {
        MessageBoxW(nullptr, message.c_str(), title.c_str(), MB_OK | MB_ICONERROR);
        return;
    }
    const auto dialogIcon = LoadIconW(nullptr, icon);
    SendMessageW(hwnd, WM_SETICON, ICON_BIG, reinterpret_cast<LPARAM>(dialogIcon));
    SendMessageW(hwnd, WM_SETICON, ICON_SMALL, reinterpret_cast<LPARAM>(dialogIcon));

    const auto edit = CreateWindowExW(
        WS_EX_CLIENTEDGE, L"EDIT", message.c_str(),
        WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL,
        0, 0, 0, 0, hwnd, reinterpret_cast<HMENU>(1), instance, nullptr);
    const auto button = CreateWindowExW(
        0, L"BUTTON", L"OK", WS_CHILD | WS_VISIBLE | BS_DEFPUSHBUTTON,
        0, 0, 0, 0, hwnd, reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDOK)), instance, nullptr);

    const auto font = reinterpret_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
    SendMessageW(edit, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    SendMessageW(button, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    SendMessageW(edit, EM_SETSEL, 0, 0);

    RECT client{};
    GetClientRect(hwnd, &client);
    SendMessageW(hwnd, WM_SIZE, 0, MAKELPARAM(client.right, client.bottom));
    SetFocus(edit);

    MSG msg;
    while (GetMessageW(&msg, nullptr, 0, 0) > 0)
    {
        if (msg.message == WM_KEYDOWN && msg.wParam == VK_ESCAPE)
        {
            DestroyWindow(hwnd);
            continue;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
}

bool SendRequest(const std::string& message)
{
    const auto pipe = CreateFileW(PipeName().c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, 0, nullptr);
    if (pipe == INVALID_HANDLE_VALUE)
        return false;
    DWORD written = 0;
    const auto success = WriteFile(pipe, message.data(), static_cast<DWORD>(message.size()), &written, nullptr) != FALSE
        && written == static_cast<DWORD>(message.size());
    CloseHandle(pipe);
    return success;
}

bool SendRequestWithRetry(const std::string& message, DWORD timeoutMilliseconds)
{
    const auto deadline = GetTickCount64() + timeoutMilliseconds;
    do
    {
        if (SendRequest(message))
            return true;
        WaitNamedPipeW(PipeName().c_str(), 100);
        Sleep(50);
    }
    while (GetTickCount64() < deadline);
    return false;
}

bool IsHook(const std::vector<std::wstring>& arguments, bool& uninstall)
{
    for (const auto& argument : arguments)
    {
        if (argument == L"--velopack-uninstall" || argument == L"--velopack-obsolete"
            || argument == L"--velopack-obsoleted" || argument == L"--squirrel-uninstall"
            || argument == L"--squirrel-obsolete" || argument == L"--squirrel-obsoleted")
        {
            uninstall = true;
            return true;
        }
        if (argument == L"--velopack-install" || argument == L"--velopack-updated"
            || argument == L"--squirrel-install" || argument == L"--squirrel-updated")
            return true;
    }
    return false;
}

void HandleHook(const fs::path& installRoot, bool uninstall)
{
    wchar_t localAppData[MAX_PATH]{};
    SHGetFolderPathW(nullptr, CSIDL_LOCAL_APPDATA, nullptr, 0, localAppData);
    const auto backupRoot = fs::path(localAppData) / "Hammer5Tools.Backup";
    const auto userData = installRoot / "userdata";
    const auto backupData = backupRoot / "userdata";
    const auto sentinel = backupRoot / "USERDATA_BACKUP_VALID";
    try
    {
        fs::create_directories(backupRoot);
        if (uninstall && fs::is_directory(userData))
        {
            fs::remove_all(backupData);
            fs::copy(userData, backupData, fs::copy_options::recursive);
            std::ofstream(sentinel) << "valid";
            Log(backupRoot, L"Backed up user data during uninstall hook.");
        }
        else if (!uninstall && fs::is_directory(backupData) && fs::exists(sentinel))
        {
            fs::remove_all(userData);
            fs::copy(backupData, userData, fs::copy_options::recursive);
            fs::remove_all(backupData);
            fs::remove(sentinel);
            Log(backupRoot, L"Restored user data during install hook.");
        }
    }
    catch (const std::exception& exception)
    {
        Log(backupRoot, L"Hook operation failed: " + std::wstring(exception.what(), exception.what() + std::strlen(exception.what())));
    }
}

std::wstring ChildArguments(const std::vector<std::wstring>& arguments)
{
    std::wstring result;
    for (const auto& argument : arguments)
    {
        if (!result.empty()) result.push_back(L' ');
        result += launcher::QuoteArgument(argument);
    }
    return result;
}

std::wstring ReadFileAsString(const fs::path& filePath)
{
    try
    {
        std::ifstream stream(filePath, std::ios::binary);
        if (!stream.is_open())
            return {};
        std::string bytes((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
        while (!bytes.empty() && (bytes.back() == '\r' || bytes.back() == '\n' || bytes.back() == ' ' || bytes.back() == '\t'))
            bytes.pop_back();
        if (bytes.empty())
            return {};
        const auto size = MultiByteToWideChar(CP_UTF8, 0, bytes.data(), static_cast<int>(bytes.size()), nullptr, 0);
        if (size > 0)
        {
            std::wstring result(size, L'\0');
            MultiByteToWideChar(CP_UTF8, 0, bytes.data(), static_cast<int>(bytes.size()), result.data(), size);
            return result;
        }
        return std::wstring(bytes.begin(), bytes.end());
    }
    catch (...)
    {
        return {};
    }
}

std::wstring ReadErrorDetails(const fs::path& directory)
{
    const auto lastCrash = directory / "last_crash.txt";
    const auto stderrLog = directory / "gui_stderr.log";

    auto content = ReadFileAsString(lastCrash);
    if (content.empty())
        content = ReadFileAsString(stderrLog);

    return content;
}

int RunGuiOnce(const fs::path& executable, const std::vector<std::wstring>& arguments,
           const fs::path& installRoot, const fs::path& appRoot, const fs::path& runtimeRoot)
{
    const auto logsDirectory = installRoot / "userdata" / "logs";
    try
    {
        fs::create_directories(logsDirectory);
        fs::remove(logsDirectory / "last_crash.txt");
        fs::remove(logsDirectory / "gui_stderr.log");
    }
    catch (...) {}

    SECURITY_ATTRIBUTES handoffSecurity{sizeof(handoffSecurity), nullptr, TRUE};
    const auto handoff = CreateEventW(&handoffSecurity, TRUE, FALSE, nullptr);
    if (handoff == nullptr)
    {
        const auto message = L"Could not create the Hammer5Tools GUI handoff. Windows error "
            + std::to_wstring(GetLastError()) + L".";
        Log(logsDirectory, message);
        ShowErrorDialog(message, L"Hammer 5 Tools Launcher");
        return 2;
    }

    SetEnvironmentVariableW(L"H5T_LAUNCHER_OWNS_INSTANCE", L"1");
    const auto handoffValue = std::to_wstring(reinterpret_cast<std::uintptr_t>(handoff));
    SetEnvironmentVariableW(L"H5T_LAUNCHER_HANDOFF", handoffValue.c_str());
    SetEnvironmentVariableW(L"H5T_INSTALL_ROOT", installRoot.c_str());
    SetEnvironmentVariableW(L"H5T_APP_ROOT", appRoot.c_str());
    SetEnvironmentVariableW(L"H5T_RUNTIME_ROOT", runtimeRoot.c_str());
    SetEnvironmentVariableW(L"H5T_USER_DATA_ROOT", (installRoot / "userdata").c_str());

    auto commandLine = L"\"" + executable.wstring() + L"\"";
    const auto childArguments = ChildArguments(arguments);
    if (!childArguments.empty()) commandLine += L" " + childArguments;
    std::vector<wchar_t> mutableCommand(commandLine.begin(), commandLine.end());
    mutableCommand.push_back(L'\0');

    SECURITY_ATTRIBUTES stdErrSa{sizeof(stdErrSa), nullptr, TRUE};
    const auto stdErrPath = logsDirectory / "gui_stderr.log";
    const auto stdErrHandle = CreateFileW(
        stdErrPath.c_str(),
        GENERIC_WRITE | GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        &stdErrSa,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr
    );

    STARTUPINFOW startup{sizeof(startup)};
    if (stdErrHandle != INVALID_HANDLE_VALUE)
    {
        startup.dwFlags |= STARTF_USESTDHANDLES;
        startup.hStdError = stdErrHandle;
        startup.hStdOutput = stdErrHandle;
        startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    }

    PROCESS_INFORMATION process{};
    const auto startedAt = GetTickCount64();
    if (!CreateProcessW(executable.c_str(), mutableCommand.data(), nullptr, nullptr, TRUE, 0, nullptr,
                        appRoot.c_str(), &startup, &process))
    {
        const auto errorCode = GetLastError();
        if (stdErrHandle != INVALID_HANDLE_VALUE)
            CloseHandle(stdErrHandle);
        CloseHandle(handoff);
        const auto message = L"Could not start the Hammer5Tools GUI. Windows error " + std::to_wstring(errorCode) + L".";
        Log(logsDirectory, message);
        ShowErrorDialog(message, L"Hammer 5 Tools Launcher");
        return 2;
    }
    if (stdErrHandle != INVALID_HANDLE_VALUE)
        CloseHandle(stdErrHandle);
    CloseHandle(handoff);
    CloseHandle(process.hThread);
    while (GetTickCount64() - startedAt < 10000)
    {
        if (WaitForSingleObject(process.hProcess, 0) == WAIT_OBJECT_0)
            break;
        if (WaitNamedPipeW(PipeName().c_str(), 100))
        {
            Log(logsDirectory, L"GUI startup completed and IPC is ready.");
            break;
        }
        Sleep(50);
    }
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD exitCode = 1;
    GetExitCodeProcess(process.hProcess, &exitCode);
    CloseHandle(process.hProcess);
    if (exitCode != 0 && exitCode != RestartExitCode)
    {
        const auto duringStartup = GetTickCount64() - startedAt < 10000;
        auto message = duringStartup
            ? L"Hammer5Tools exited during startup with code " + std::to_wstring(exitCode) + L"."
            : L"Hammer5ToolsGUI.exe exited unexpectedly with code " + std::to_wstring(exitCode) + L".";

        const auto errorDetails = ReadErrorDetails(logsDirectory);
        if (!errorDetails.empty())
        {
            auto displayDetails = errorDetails;
            if (displayDetails.size() > 2000)
                displayDetails = displayDetails.substr(0, 1950) + L"\n... [truncated, see logs for full details]";
            message += L"\n\n" + displayDetails;
        }

        message += L"\n\nLog folder:\n" + logsDirectory.wstring();

        Log(logsDirectory, message);
        ShowErrorDialog(message, duringStartup ? L"Hammer 5 Tools Startup Failure" : L"Hammer 5 Tools Crash");
    }
    return static_cast<int>(exitCode);
}
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int)
{
    int argumentCount = 0;
    auto nativeArguments = CommandLineToArgvW(GetCommandLineW(), &argumentCount);
    if (nativeArguments == nullptr)
        return 1;
    std::vector<std::wstring> arguments;
    for (auto index = 1; index < argumentCount; index++)
        arguments.emplace_back(nativeArguments[index]);
    LocalFree(nativeArguments);

    const auto installRoot = ExecutablePath().parent_path();
    bool uninstall = false;
    if (IsHook(arguments, uninstall))
    {
        HandleHook(installRoot, uninstall);
        return 0;
    }

    const auto message = launcher::SerializeRequest(launcher::ParseRequest(arguments, fs::current_path()));
    if (SendRequest(message))
        return 0;

    const auto mutex = CreateMutexW(nullptr, TRUE, MutexName().c_str());
    if (mutex == nullptr)
        return 1;
    if (GetLastError() == ERROR_ALREADY_EXISTS)
    {
        if (SendRequestWithRetry(message, 10000))
        {
            CloseHandle(mutex);
            return 0;
        }
        const auto waitResult = WaitForSingleObject(mutex, 5000);
        if (waitResult != WAIT_OBJECT_0 && waitResult != WAIT_ABANDONED_0)
        {
            CloseHandle(mutex);
            ShowErrorDialog(L"The existing Hammer5Tools instance did not accept the request.",
                            L"Hammer 5 Tools", IDI_WARNING);
            return 3;
        }
    }

    const auto appRoot = installRoot / "app";
    const auto runtimeRoot = appRoot / "runtime";
    const auto guiExecutable = appRoot / "Hammer5ToolsGUI.exe";
    if (!fs::exists(guiExecutable))
    {
        ReleaseMutex(mutex);
        CloseHandle(mutex);
        ShowErrorDialog(L"app\\Hammer5ToolsGUI.exe is missing from the application payload.",
                        L"Hammer 5 Tools Launcher");
        return 2;
    }
    auto childArguments = arguments;
    auto exitCode = RunGuiOnce(guiExecutable, childArguments, installRoot, guiExecutable.parent_path(), runtimeRoot);
    while (exitCode == RestartExitCode)
    {
        Log(installRoot / "userdata" / "logs", L"Restart requested by GUI.");
        childArguments.clear();
        exitCode = RunGuiOnce(guiExecutable, childArguments, installRoot, guiExecutable.parent_path(), runtimeRoot);
    }
    ReleaseMutex(mutex);
    CloseHandle(mutex);
    return exitCode;
}
