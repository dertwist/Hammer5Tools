#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#include <vector>
#include <filesystem>

namespace fs = std::filesystem;

struct BuildInfo {
    std::string version;
    std::string channel;
    std::string build_date;
    std::string commit_sha;
};

enum NotifyType {
    NOTIFY_NONE,
    NOTIFY_STABLE_AVAILABLE,
    NOTIFY_STABLE_FROM_DEV,
    NOTIFY_DEV_UPDATE
};

struct ReleaseInfo {
    bool found = false;
    std::string version;
    std::string release_url;
    std::string publish_date;
    std::string commit_sha;
    std::string download_url;
    std::string sha256;
    bool is_prerelease = false;
    NotifyType notify_type = NOTIFY_NONE;
};

class UpdateManager {
public:
    static BuildInfo GetLocalBuildInfo();
    static ReleaseInfo CheckForUpdates(const BuildInfo& local);
    
    static bool DownloadFile(const std::string& url, const fs::path& destPath);
    static bool VerifyFileHash(const fs::path& path, const std::string& expectedHash);
    static bool ExtractZip(const fs::path& zipPath, const fs::path& destDir);

    static void RunReplaceMode(int targetPid, const fs::path& srcDir, const fs::path& dstDir);
    static void RunCleanupMode(const fs::path& appDir);

private:
    static std::string HttpGet(const std::wstring& host, const std::wstring& path, bool isGithub = true);
    static BuildInfo FetchRemoteVersionTxt(const std::string& tag);
    static ReleaseInfo FetchRelease(const std::string& api_path);
    static bool SemverGreater(const std::string& a, const std::string& b);
};
