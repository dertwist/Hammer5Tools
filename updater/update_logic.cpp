#include "update_logic.h"
#include <windows.h>
#include <winhttp.h>
#include <tlhelp32.h>
#include <iostream>
#include <fstream>
#include "third_party/miniz.h"

#pragma comment(lib, "winhttp.lib")

ReleaseInfo UpdateLogic::CheckForUpdates(const std::string& current_version) {
    ReleaseInfo info;
    HINTERNET hSession = WinHttpOpen(L"Hammer5ToolsUpdater/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) return info;

    HINTERNET hConnect = WinHttpConnect(hSession, L"api.github.com", INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return info; }

    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", L"/repos/dertwist/Hammer5Tools/releases/latest", NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return info; }

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

            // Manual JSON parsing for "tag_name": "v..." and "browser_download_url": "..."
            size_t tag_pos = response.find("\"tag_name\":");
            if (tag_pos != std::string::npos) {
                size_t start = response.find("\"", tag_pos + 11) + 1;
                size_t end = response.find("\"", start);
                info.version = response.substr(start, end - start);
                
                if (info.version != current_version) {
                    size_t asset_pos = response.find("\"browser_download_url\":");
                    if (asset_pos != std::string::npos) {
                        size_t d_start = response.find("\"", asset_pos + 23) + 1;
                        size_t d_end = response.find("\"", d_start);
                        info.download_url = response.substr(d_start, d_end - d_start);
                        info.found = true;
                    }
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
        if (!mz_zip_reader_get_stat(&zip_archive, i, &file_stat)) continue;

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
