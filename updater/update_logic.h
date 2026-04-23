#pragma once
#include <string>
#include <vector>
#include <functional>

enum NotifyType {
    NOTIFY_NONE,
    NOTIFY_STABLE_AVAILABLE,   // stable user, newer stable exists
    NOTIFY_DEV_UPDATE,         // dev user, newer dev build exists
    NOTIFY_STABLE_FROM_DEV     // dev user, a stable release is now out
};

struct BuildInfo {
    std::string version;       // line 1 of version.txt
    std::string channel;       // line 2: "stable" or "dev"
    std::string build_date;    // line 3: ISO 8601 UTC
};

struct ReleaseInfo {
    bool found = false;
    bool is_prerelease = false;
    std::string version;
    std::string release_url;   // html_url from GitHub API (for "View on GitHub" button)
    std::string publish_date;  // published_at from GitHub API
    std::string commit_sha;
    NotifyType notify_type = NOTIFY_NONE;
};

class UpdateLogic {
public:
    static BuildInfo GetBuildInfo();
    static ReleaseInfo CheckForUpdates(const BuildInfo& local);
    static void KillProcess(const std::wstring& process_name);
    static bool IsProcessRunning(const std::wstring& process_name);

private:
    static ReleaseInfo FetchRelease(const std::string& api_path);
    static BuildInfo   FetchRemoteVersionTxt(const std::string& tag);
    static bool        SemverGreater(const std::string& a, const std::string& b);
};
