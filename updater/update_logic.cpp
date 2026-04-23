#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <tlhelp32.h>
#include <iostream>
#include <fstream>
#include <filesystem>
#include "update_logic.h"
#include "third_party/miniz.h"

#pragma comment(lib, "winhttp.lib")

ReleaseInfo UpdateLogic::CheckForUpdates(const std::string& current_version) {
    ReleaseInfo info;
    
    // Get dev_builds setting from user/settings.ini
    wchar_t exePath[MAX_PATH];
    GetModuleFileNameW(NULL, exePath, MAX_PATH);
    std::filesystem::path root = std::filesystem::path(exePath).parent_path();
    std::wstring iniPath = (root / L"settings.ini").wstring();
    
    bool devBuilds = GetPrivateProfileIntW(L"APP", L"dev_builds", 0, iniPath.c_str()) != 0;

    HINTERNET hSession = WinHttpOpen(L"Hammer5ToolsUpdater/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) return info;

    HINTERNET hConnect = WinHttpConnect(hSession, L"api.github.com", INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return info; }

    // Use /releases instead of /releases/latest to see pre-releases
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", L"/repos/dertwist/Hammer5Tools/releases", NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return info; }

    // Add User-Agent header (required by GitHub API)
    WinHttpAddRequestHeaders(hRequest, L"User-Agent: Hammer5ToolsUpdater/1.0\r\n", (ULONG)-1L, WINHTTP_ADDREQ_FLAG_ADD);

    if (WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
        if (WinHttpReceiveResponse(hRequest, NULL)) {
            std::string response;
            DWORD dwSize = 0;
            do {
                if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
                if (dwSize == 0) break;
                char* pszOutBuffer = new char[dwSize + 1];
                DWORD dwDownloaded = 0;
                if (WinHttpReadData(hRequest, (LPVOID)pszOutBuffer, dwSize, &dwDownloaded)) {
                    pszOutBuffer[dwDownloaded] = 0;
                    response += pszOutBuffer;
                }
                delete[] pszOutBuffer;
            } while (dwSize > 0);

            // Manual JSON array parsing with better object detection
            size_t pos = 0;
            while (true) {
                size_t start = response.find("{", pos);
                if (start == std::string::npos) break;
                
                // Find matching closing brace to avoid truncating at nested objects
                size_t end = std::string::npos;
                int braceCount = 0;
                for (size_t i = start; i < response.length(); ++i) {
                    if (response[i] == '{') braceCount++;
                    else if (response[i] == '}') braceCount--;
                    if (braceCount == 0) {
                        end = i;
                        break;
                    }
                }
                if (end == std::string::npos) break;
                
                std::string releaseJson = response.substr(start, end - start + 1);
                pos = end + 1;
                
                auto getField = [&](const std::string& key) -> std::string {
                    size_t kPos = releaseJson.find("\"" + key + "\":");
                    if (kPos == std::string::npos) return "";
                    size_t vStart = releaseJson.find("\"", kPos + key.length() + 2);
                    if (vStart == std::string::npos) return "";
                    size_t vEnd = releaseJson.find("\"", vStart + 1);
                    if (vEnd == std::string::npos) return "";
                    return releaseJson.substr(vStart + 1, vEnd - vStart - 1);
                };
                
                auto getBoolField = [&](const std::string& key) -> bool {
                    size_t kPos = releaseJson.find("\"" + key + "\":");
                    if (kPos == std::string::npos) return false;
                    size_t vStart = kPos + key.length() + 2;
                    while (vStart < releaseJson.length() && (releaseJson[vStart] == ' ' || releaseJson[vStart] == ':')) vStart++;
                    return releaseJson.compare(vStart, 4, "true") == 0;
                };
                
                bool isPrerelease = getBoolField("prerelease");
                bool isDraft = getBoolField("draft");
                
                if (isDraft) continue;
                if (isPrerelease && !devBuilds) continue;
                
                std::string tag = getField("tag_name");
                std::string body = getField("body");
                std::string date = getField("published_at");
                std::string commit = getField("target_commitish");
                
                // Find download URL for hammer5tools.zip
                size_t assetPos = 0;
                std::string downloadUrl;
                while ((assetPos = releaseJson.find("\"browser_download_url\":", assetPos)) != std::string::npos) {
                    size_t dStart = releaseJson.find("\"", assetPos + 23) + 1;
                    size_t dEnd = releaseJson.find("\"", dStart);
                    std::string url = releaseJson.substr(dStart, dEnd - dStart);
                    if (url.find("hammer5tools.zip") != std::string::npos) {
                        downloadUrl = url;
                        break;
                    }
                    assetPos = dEnd;
                }
                
                // Fallback to first asset if hammer5tools.zip not found
                if (downloadUrl.empty()) {
                    assetPos = releaseJson.find("\"browser_download_url\":");
                    if (assetPos != std::string::npos) {
                        size_t dStart = releaseJson.find("\"", assetPos + 23) + 1;
                        size_t dEnd = releaseJson.find("\"", dStart);
                        downloadUrl = releaseJson.substr(dStart, dEnd - dStart);
                    }
                }
                
                if (!tag.empty() && !downloadUrl.empty()) {
                    std::string cleanTag = tag;
                    if (cleanTag[0] == 'v') cleanTag = cleanTag.substr(1);
                    std::string cleanCurrent = current_version;
                    if (cleanCurrent[0] == 'v') cleanCurrent = cleanCurrent.substr(1);
                    
                    // Special case: if on dev version, we always check if the published date is newer?
                    // For now, just allow updating if tag is different.
                    if (cleanTag != cleanCurrent) {
                        info.version = tag;
                        info.download_url = downloadUrl;
                        info.publish_date = date;
                        info.commit_sha = commit;
                        info.is_prerelease = isPrerelease;
                        
                        // Simple unescape for \r\n
                        std::string unescapedBody = body;
                        size_t rPos;
                        while ((rPos = unescapedBody.find("\\r\\n")) != std::string::npos) unescapedBody.replace(rPos, 4, "\r\n");
                        while ((rPos = unescapedBody.find("\\n")) != std::string::npos) unescapedBody.replace(rPos, 2, "\n");
                        
                        info.changelog = unescapedBody;
                        info.found = true;
                        break; // Found a valid update, stop searching
                    } else if (cleanTag == "dev") {
                        // If we are on dev and the latest is also dev, we might still want to update 
                        // if the user explicitly checks. But we need a way to know if it's NEWER.
                        // For now, if the tag is 'dev', we'll only offer it if the current version is NOT 'dev'.
                        // To support dev-to-dev updates, we'd need to store the commit SHA locally.
                    }
                    
                    // If this release is the same as current, stop searching older releases
                    if (cleanTag == cleanCurrent) break;
                }
            }
        }
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return info;
}

bool UpdateLogic::DownloadFile(const std::string& url, const std::string& destination, std::function<void(float)> progress_callback) {
    // Basic redirect support would be needed for GitHub assets
    // For simplicity, we'll assume the URL is direct or use WinHTTP's automatic redirect
    
    std::wstring wurl(url.begin(), url.end()); // Simple conversion for ASCII URLs
    
    URL_COMPONENTS urlComp = { sizeof(urlComp) };
    urlComp.dwHostNameLength = (DWORD)-1;
    urlComp.dwUrlPathLength = (DWORD)-1;
    urlComp.dwExtraInfoLength = (DWORD)-1;

    if (!WinHttpCrackUrl(wurl.c_str(), 0, 0, &urlComp)) return false;

    std::wstring host(urlComp.lpszHostName, urlComp.dwHostNameLength);
    std::wstring path(urlComp.lpszUrlPath, urlComp.dwUrlPathLength + urlComp.dwExtraInfoLength);

    HINTERNET hSession = WinHttpOpen(L"Hammer5ToolsUpdater/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), urlComp.nPort, 0);
    
    DWORD dwOpenFlags = (urlComp.nPort == INTERNET_DEFAULT_HTTPS_PORT) ? WINHTTP_FLAG_SECURE : 0;
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", path.c_str(), NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, dwOpenFlags);

    if (!WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) return false;
    if (!WinHttpReceiveResponse(hRequest, NULL)) return false;

    DWORD dwContentLength = 0;
    DWORD dwSize = sizeof(dwContentLength);
    WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_CONTENT_LENGTH | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX, &dwContentLength, &dwSize, WINHTTP_NO_HEADER_INDEX);

    std::ofstream file(destination, std::ios::binary);
    if (!file.is_open()) return false;

    DWORD dwDownloaded = 0;
    DWORD dwTotalDownloaded = 0;
    char buffer[8192];
    do {
        if (!WinHttpReadData(hRequest, (LPVOID)buffer, sizeof(buffer), &dwDownloaded)) break;
        if (dwDownloaded == 0) break;
        file.write(buffer, dwDownloaded);
        dwTotalDownloaded += dwDownloaded;
        if (dwContentLength > 0) {
            progress_callback((float)dwTotalDownloaded / dwContentLength);
        }
    } while (dwDownloaded > 0);

    file.close();
    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return true;
}

bool UpdateLogic::ExtractZip(const std::string& zip_path, const std::string& extract_path) {
    mz_zip_archive zip_archive;
    memset(&zip_archive, 0, sizeof(zip_archive));

    if (!mz_zip_reader_init_file(&zip_archive, zip_path.c_str(), 0)) return false;

    mz_uint num_files = mz_zip_reader_get_num_files(&zip_archive);
    for (mz_uint i = 0; i < num_files; i++) {
        mz_zip_archive_file_stat file_stat;
        if (!mz_zip_reader_file_stat(&zip_archive, i, &file_stat)) continue;

        std::string dest_file = extract_path + "\\" + file_stat.m_filename;
        
        // Ensure directory exists
        std::string dir = dest_file.substr(0, dest_file.find_last_of("\\/"));
        CreateDirectoryA(dir.c_str(), NULL); // Simple non-recursive CreateDirectory

        if (mz_zip_reader_is_file_a_directory(&zip_archive, i)) {
            CreateDirectoryA(dest_file.c_str(), NULL);
        } else {
            mz_zip_reader_extract_to_file(&zip_archive, i, dest_file.c_str(), 0);
        }
    }

    mz_zip_reader_end(&zip_archive);
    return true;
}

void UpdateLogic::KillProcess(const std::wstring& process_name) {
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return;

    PROCESSENTRY32W pe;
    pe.dwSize = sizeof(pe);

    if (Process32FirstW(hSnap, &pe)) {
        do {
            if (process_name == pe.szExeFile) {
                HANDLE hProc = OpenProcess(PROCESS_TERMINATE, FALSE, pe.th32ProcessID);
                if (hProc) {
                    TerminateProcess(hProc, 0);
                    CloseHandle(hProc);
                }
            }
        } while (Process32NextW(hSnap, &pe));
    }
    CloseHandle(hSnap);
}

bool UpdateLogic::IsProcessRunning(const std::wstring& process_name) {
    bool running = false;
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return false;

    PROCESSENTRY32W pe;
    pe.dwSize = sizeof(pe);

    if (Process32FirstW(hSnap, &pe)) {
        do {
            if (process_name == pe.szExeFile) {
                running = true;
                break;
            }
        } while (Process32NextW(hSnap, &pe));
    }
    CloseHandle(hSnap);
    return running;
}
