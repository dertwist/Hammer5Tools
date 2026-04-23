#pragma once
#include <string>
#include <vector>
#include <functional>

struct ReleaseInfo {
    bool found = false;
    std::string version;
    std::string download_url;
    std::string changelog;
};

class UpdateLogic {
public:
    static ReleaseInfo CheckForUpdates(const std::string& current_version);
    static bool DownloadFile(const std::string& url, const std::string& destination, std::function<void(float)> progress_callback);
    static bool ExtractZip(const std::string& zip_path, const std::string& extract_path);
    static void KillProcess(const std::wstring& process_name);
    static bool IsProcessRunning(const std::wstring& process_name);
};
