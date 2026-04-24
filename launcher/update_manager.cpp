#include "update_manager.h"
#include <winhttp.h>
#include <bcrypt.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <tlhelp32.h>
#include <shlwapi.h>
#include <shellapi.h>
#include "miniz.h"


#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "shlwapi.lib")

namespace fs = std::filesystem;

// Helper to convert string to wstring
static std::wstring to_wstring(const std::string& s) {
    if (s.empty()) return L"";
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &s[0], (int)s.size(), NULL, 0);
    std::wstring strTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &s[0], (int)s.size(), &strTo[0], size_needed);
    return strTo;
}

static std::string to_utf8(const std::wstring& ws) {
    if (ws.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &ws[0], (int)ws.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &ws[0], (int)ws.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

static std::string NormaliseDate(const std::string& s) {
    std::string r = s;
    while (!r.empty() && (r.back() == '\r' || r.back() == '\n' || r.back() == ' ')) r.pop_back();
    if (r.size() >= 6 && r.substr(r.size() - 6) == "+00:00") r = r.substr(0, r.size() - 6) + "Z";
    return r;
}

static std::string JsonString(const std::string& json, const std::string& key) {
    size_t kPos = json.find("\"" + key + "\":");
    if (kPos == std::string::npos) return "";
    size_t vStart = json.find("\"", kPos + key.length() + 2);
    if (vStart == std::string::npos) return "";
    size_t vEnd = json.find("\"", vStart + 1);
    if (vEnd == std::string::npos) return "";
    return json.substr(vStart + 1, vEnd - vStart - 1);
}

static bool JsonBool(const std::string& json, const std::string& key) {
    size_t kPos = json.find("\"" + key + "\":");
    if (kPos == std::string::npos) return false;
    size_t vStart = kPos + key.length() + 2;
    while (vStart < json.length() && (json[vStart] == ' ' || json[vStart] == ':')) vStart++;
    return json.compare(vStart, 4, "true") == 0;
}

std::string UpdateManager::HttpGet(const std::wstring& host, const std::wstring& path, bool isGithub) {
    std::string result;
    HINTERNET hSession = WinHttpOpen(L"Hammer5Tools/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);
    if (!hSession) return result;

    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return result; }

    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", path.c_str(), NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return result; }

    if (isGithub) {
        WinHttpAddRequestHeaders(hRequest, L"User-Agent: Hammer5Tools/1.0\r\n", (ULONG)-1L, WINHTTP_ADDREQ_FLAG_ADD);
        WinHttpAddRequestHeaders(hRequest, L"Accept: application/vnd.github+json\r\n", (ULONG)-1L, WINHTTP_ADDREQ_FLAG_ADD);
    }

    DWORD policy = WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS;
    WinHttpSetOption(hRequest, WINHTTP_OPTION_REDIRECT_POLICY, &policy, sizeof(policy));

    if (WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
        if (WinHttpReceiveResponse(hRequest, NULL)) {
            DWORD statusCode = 0;
            DWORD statusSize = sizeof(statusCode);
            WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, NULL, &statusCode, &statusSize, NULL);
            if (statusCode == 200) {
                DWORD dwSize = 0;
                do {
                    if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
                    if (dwSize == 0) break;
                    char* buf = new char[dwSize + 1];
                    DWORD dwRead = 0;
                    if (WinHttpReadData(hRequest, (LPVOID)buf, dwSize, &dwRead)) {
                        buf[dwRead] = 0;
                        result.append(buf, dwRead);
                    }
                    delete[] buf;
                } while (dwSize > 0);
            }
        }
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return result;
}

BuildInfo UpdateManager::FetchRemoteVersionTxt(const std::string& tag) {
    BuildInfo remote;
    remote.channel = "stable";
    std::string body = HttpGet(L"github.com", L"/dertwist/Hammer5Tools/releases/download/" + to_wstring(tag) + L"/version.txt");
    if (body.empty()) return remote;

    std::istringstream ss(body);
    std::string line;
    if (std::getline(ss, line)) {
        while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) line.pop_back();
        remote.version = line;
    }
    if (std::getline(ss, line)) {
        while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) line.pop_back();
        if (!line.empty()) remote.channel = line;
    }
    if (std::getline(ss, line)) remote.build_date = NormaliseDate(line);
    if (std::getline(ss, line)) {
        while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) line.pop_back();
        if (!line.empty()) remote.commit_sha = line;
    }
    return remote;
}

ReleaseInfo UpdateManager::FetchRelease(const std::string& api_path) {
    ReleaseInfo info;
    std::string body = HttpGet(L"api.github.com", to_wstring(api_path));
    if (body.empty()) return info;

    size_t start = body.find('{');
    if (start == std::string::npos) return info;
    
    // Primitive asset extraction for download_url
    // In a real app we'd use a JSON parser, but here we'll grep for the first .zip asset
    size_t assetPos = body.find("\"browser_download_url\":");
    if (assetPos != std::string::npos) {
        size_t vStart = body.find("\"", assetPos + 23);
        size_t vEnd = body.find("\"", vStart + 1);
        if (vStart != std::string::npos && vEnd != std::string::npos) {
            info.download_url = body.substr(vStart + 1, vEnd - vStart - 1);
        }
    }

    info.found = true;
    info.version = JsonString(body, "tag_name");
    if (!info.version.empty() && info.version[0] == 'v') info.version = info.version.substr(1);
    info.release_url = JsonString(body, "html_url");
    info.publish_date = JsonString(body, "published_at");
    info.commit_sha = JsonString(body, "target_commitish");
    info.is_prerelease = JsonBool(body, "prerelease");
    return info;
}

bool UpdateManager::SemverGreater(const std::string& a, const std::string& b) {
    auto parse = [](const std::string& v, int& maj, int& min, int& pat) -> bool {
        std::string s = v;
        if (!s.empty() && s[0] == 'v') s = s.substr(1);
        auto dash = s.find('-');
        if (dash != std::string::npos) s = s.substr(0, dash);
        return sscanf(s.c_str(), "%d.%d.%d", &maj, &min, &pat) == 3;
    };
    int aM=0, am=0, ap=0, bM=0, bm=0, bp=0;
    if (!parse(a, aM, am, ap)) return false;
    if (!parse(b, bM, bm, bp)) return false;
    if (aM != bM) return aM > bM;
    if (am != bm) return am > bm;
    return ap > bp;
}

BuildInfo UpdateManager::GetLocalBuildInfo() {
    wchar_t buffer[MAX_PATH];
    GetModuleFileNameW(NULL, buffer, MAX_PATH);
    fs::path exeDir = fs::path(buffer).parent_path();
    BuildInfo info;
    info.channel = "stable";

    fs::path vfPath = exeDir / "app" / "version.txt";
    if (!fs::exists(vfPath)) vfPath = exeDir / "version.txt";

    std::ifstream vf(vfPath);
    if (vf.is_open()) {
        std::string line;
        if (std::getline(vf, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) line.pop_back();
            info.version = line;
        }
        if (std::getline(vf, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) line.pop_back();
            if (!line.empty()) info.channel = line;
        }
        if (std::getline(vf, line)) info.build_date = NormaliseDate(line);
        if (std::getline(vf, line)) {
            while (!line.empty() && (line.back() == '\r' || line.back() == '\n')) line.pop_back();
            if (!line.empty()) info.commit_sha = line;
        }
    }
    return info;
}

ReleaseInfo UpdateManager::CheckForUpdates(const BuildInfo& local) {
    ReleaseInfo stable = FetchRelease("/repos/dertwist/Hammer5Tools/releases/latest");
    if (local.channel != "dev") {
        if (stable.found && SemverGreater(stable.version, local.version)) {
            stable.notify_type = NOTIFY_STABLE_AVAILABLE;
            return stable;
        }
    } else {
        if (stable.found && SemverGreater(stable.version, local.version)) {
            stable.notify_type = NOTIFY_STABLE_FROM_DEV;
            return stable;
        }
        BuildInfo remoteDev = FetchRemoteVersionTxt("dev");
        if (!remoteDev.build_date.empty() && !local.build_date.empty() && remoteDev.build_date > local.build_date) {
            ReleaseInfo dev = FetchRelease("/repos/dertwist/Hammer5Tools/releases/tags/dev");
            dev.notify_type = NOTIFY_DEV_UPDATE;
            dev.publish_date = remoteDev.build_date;
            return dev;
        }
    }
    return {};
}

bool UpdateManager::DownloadFile(const std::string& url, const fs::path& destPath) {
    std::wstring wurl = to_wstring(url);
    URL_COMPONENTS urlComp = { sizeof(urlComp) };
    urlComp.dwHostNameLength = (DWORD)-1;
    urlComp.dwUrlPathLength = (DWORD)-1;
    urlComp.dwExtraInfoLength = (DWORD)-1;

    if (!WinHttpCrackUrl(wurl.c_str(), 0, 0, &urlComp)) return false;

    std::wstring host(urlComp.lpszHostName, urlComp.dwHostNameLength);
    std::wstring path(urlComp.lpszUrlPath, urlComp.dwUrlPathLength + urlComp.dwExtraInfoLength);

    HINTERNET hSession = WinHttpOpen(L"Hammer5Tools/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, NULL, NULL, 0);
    if (!hSession) return false;

    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), urlComp.nPort, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return false; }

    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", path.c_str(), NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, (urlComp.nScheme == INTERNET_SCHEME_HTTPS ? WINHTTP_FLAG_SECURE : 0));
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return false; }

    DWORD policy = WINHTTP_OPTION_REDIRECT_POLICY_ALWAYS;
    WinHttpSetOption(hRequest, WINHTTP_OPTION_REDIRECT_POLICY, &policy, sizeof(policy));

    bool success = false;
    if (WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
        if (WinHttpReceiveResponse(hRequest, NULL)) {
            DWORD statusCode = 0;
            DWORD statusSize = sizeof(statusCode);
            WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, NULL, &statusCode, &statusSize, NULL);
            if (statusCode == 200) {
                std::ofstream ofs(destPath, std::ios::binary);
                if (ofs.is_open()) {
                    DWORD dwSize = 0;
                    do {
                        if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
                        if (dwSize == 0) break;
                        char* buf = new char[dwSize];
                        DWORD dwRead = 0;
                        if (WinHttpReadData(hRequest, (LPVOID)buf, dwSize, &dwRead)) {
                            ofs.write(buf, dwRead);
                        }
                        delete[] buf;
                    } while (dwSize > 0);
                    success = true;
                }
            }
        }
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return success;
}

bool UpdateManager::VerifyFileHash(const fs::path& path, const std::string& expectedHash) {
    if (expectedHash.empty()) return true; // No hash to verify

    BCRYPT_ALG_HANDLE hAlg = NULL;
    BCRYPT_HASH_HANDLE hHash = NULL;
    DWORD cbHash = 0, cbHashObject = 0, cbData = 0;
    
    if (BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_SHA256_ALGORITHM, NULL, 0) != 0) return false;
    cbData = sizeof(DWORD);
    if (BCryptGetProperty(hAlg, BCRYPT_HASH_LENGTH, (PBYTE)&cbHash, cbData, &cbData, 0) != 0) { BCryptCloseAlgorithmProvider(hAlg, 0); return false; }
    if (BCryptGetProperty(hAlg, BCRYPT_OBJECT_LENGTH, (PBYTE)&cbHashObject, cbData, &cbData, 0) != 0) { BCryptCloseAlgorithmProvider(hAlg, 0); return false; }

    PBYTE pbHashObject = new BYTE[cbHashObject];
    if (BCryptCreateHash(hAlg, &hHash, pbHashObject, cbHashObject, NULL, 0, 0) != 0) { delete[] pbHashObject; BCryptCloseAlgorithmProvider(hAlg, 0); return false; }

    std::ifstream ifs(path, std::ios::binary);
    if (!ifs.is_open()) { BCryptDestroyHash(hHash); delete[] pbHashObject; BCryptCloseAlgorithmProvider(hAlg, 0); return false; }

    char buf[1024 * 64];
    while (ifs.read(buf, sizeof(buf)) || ifs.gcount() > 0) {
        BCryptHashData(hHash, (PBYTE)buf, (ULONG)ifs.gcount(), 0);
    }

    PBYTE pbHash = new BYTE[cbHash];
    BCryptFinishHash(hHash, pbHash, cbHash, 0);

    std::stringstream ss;
    for (DWORD i = 0; i < cbHash; i++) ss << std::hex << std::setw(2) << std::setfill('0') << (int)pbHash[i];
    std::string actualHash = ss.str();

    delete[] pbHash;
    BCryptDestroyHash(hHash);
    delete[] pbHashObject;
    BCryptCloseAlgorithmProvider(hAlg, 0);

    // Case-insensitive compare
    return _stricmp(actualHash.c_str(), expectedHash.c_str()) == 0;
}

bool UpdateManager::ExtractZip(const fs::path& zipPath, const fs::path& destDir) {
    mz_zip_archive zip_archive;
    memset(&zip_archive, 0, sizeof(zip_archive));

    std::string zipPathStr = to_utf8(zipPath.wstring());
    if (!mz_zip_reader_init_file(&zip_archive, zipPathStr.c_str(), 0)) return false;

    mz_uint num_files = mz_zip_reader_get_num_files(&zip_archive);
    for (mz_uint i = 0; i < num_files; i++) {
        mz_zip_archive_file_stat file_stat;
        if (!mz_zip_reader_file_stat(&zip_archive, i, &file_stat)) continue;


        fs::path outPath = destDir / file_stat.m_filename;
        if (file_stat.m_is_directory) {
            fs::create_directories(outPath);
        } else {
            fs::create_directories(outPath.parent_path());
            std::string outPathStr = to_utf8(outPath.wstring());
            mz_zip_reader_extract_to_file(&zip_archive, i, outPathStr.c_str(), 0);
        }
    }

    mz_zip_reader_end(&zip_archive);
    return true;
}

void UpdateManager::RunReplaceMode(int targetPid, const fs::path& srcDir, const fs::path& dstDir) {
    // 1. Wait for process to exit
    HANDLE hProc = OpenProcess(SYNCHRONIZE, FALSE, targetPid);
    if (hProc) {
        WaitForSingleObject(hProc, 15000); // Wait up to 15 seconds
        CloseHandle(hProc);
    }

    // Give the OS a moment to release file locks
    Sleep(500);

    bool success = true;
    std::vector<std::pair<fs::path, fs::path>> movedFiles;

    try {
        for (auto const& dir_entry : fs::recursive_directory_iterator(srcDir)) {
            if (dir_entry.is_regular_file()) {
                fs::path rel = fs::relative(dir_entry.path(), srcDir);
                fs::path target = dstDir / rel;
                fs::create_directories(target.parent_path());
                
                if (fs::exists(target)) {
                    fs::path old = target;
                    old += L".old";
                    // Rename existing file to .old
                    if (!MoveFileExW(target.c_str(), old.c_str(), MOVEFILE_REPLACE_EXISTING)) {
                        // If rename fails, we might still be locked. Try a few times.
                        bool renamed = false;
                        for(int retry=0; retry<10; retry++) {
                            Sleep(200);
                            if (MoveFileExW(target.c_str(), old.c_str(), MOVEFILE_REPLACE_EXISTING)) {
                                renamed = true;
                                break;
                            }
                        }
                        if (!renamed) {
                            success = false;
                            break;
                        }
                    }
                    movedFiles.push_back({target, old});
                }
                
                // Copy new file
                if (!fs::copy_file(dir_entry.path(), target, fs::copy_options::overwrite_existing)) {
                    success = false;
                    break;
                }
            }
        }
    } catch (...) {
        success = false;
    }

    if (!success) {
        // Rollback: move .old files back
        for (auto const& pair : movedFiles) {
            if (fs::exists(pair.second)) {
                MoveFileExW(pair.second.c_str(), pair.first.c_str(), MOVEFILE_REPLACE_EXISTING);
            }
        }
        // Launch old version with error
        fs::path oldExe = dstDir / "Hammer5Tools.exe";
        ShellExecuteW(NULL, L"open", oldExe.c_str(), L"--mode launcher --update-failed", NULL, SW_SHOWNORMAL);
    } else {
        // Launch new version
        fs::path newExe = dstDir / "Hammer5Tools.exe";
        ShellExecuteW(NULL, L"open", newExe.c_str(), L"--mode cleanup", NULL, SW_SHOWNORMAL);
    }
}


void UpdateManager::RunCleanupMode(const fs::path& appDir) {
    try {
        for (auto const& dir_entry : fs::recursive_directory_iterator(appDir)) {
            if (dir_entry.is_regular_file() && dir_entry.path().extension() == L".old") {
                fs::remove(dir_entry.path());
            }
        }
    } catch (...) {}
}
