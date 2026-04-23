#define WIN32_LEAN_AND_MEAN
#include "update_logic.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <tlhelp32.h>
#include <windows.h>
#include <winhttp.h>

#pragma comment(lib, "winhttp.lib")

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// Helper: perform a single GET request to api.github.com and return the body.
// ---------------------------------------------------------------------------
static std::string HttpGetGitHub(const std::string &api_path) {
  std::string result;

  HINTERNET hSession =
      WinHttpOpen(L"Hammer5ToolsUpdater/1.0", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                  WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
  if (!hSession)
    return result;

  HINTERNET hConnect = WinHttpConnect(hSession, L"api.github.com",
                                      INTERNET_DEFAULT_HTTPS_PORT, 0);
  if (!hConnect) {
    WinHttpCloseHandle(hSession);
    return result;
  }

  std::wstring wpath(api_path.begin(), api_path.end());
  HINTERNET hRequest = WinHttpOpenRequest(
      hConnect, L"GET", wpath.c_str(), NULL, WINHTTP_NO_REFERER,
      WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
  if (!hRequest) {
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return result;
  }

  WinHttpAddRequestHeaders(hRequest, L"User-Agent: Hammer5ToolsUpdater/1.0\r\n",
                           (ULONG)-1L, WINHTTP_ADDREQ_FLAG_ADD);
  WinHttpAddRequestHeaders(hRequest, L"Accept: application/vnd.github+json\r\n",
                           (ULONG)-1L, WINHTTP_ADDREQ_FLAG_ADD);

  if (WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                         WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
    if (WinHttpReceiveResponse(hRequest, NULL)) {
      DWORD dwSize = 0;
      do {
        if (!WinHttpQueryDataAvailable(hRequest, &dwSize))
          break;
        if (dwSize == 0)
          break;
        char *buf = new char[dwSize + 1];
        DWORD dwRead = 0;
        if (WinHttpReadData(hRequest, (LPVOID)buf, dwSize, &dwRead)) {
          buf[dwRead] = 0;
          result += buf;
        }
        delete[] buf;
      } while (dwSize > 0);
    }
  }

  WinHttpCloseHandle(hRequest);
  WinHttpCloseHandle(hConnect);
  WinHttpCloseHandle(hSession);
  return result;
}

// ---------------------------------------------------------------------------
// Helper: extract a JSON string field value from a flat object.
// ---------------------------------------------------------------------------
static std::string JsonString(const std::string &json, const std::string &key) {
  size_t kPos = json.find("\"" + key + "\":");
  if (kPos == std::string::npos)
    return "";
  size_t vStart = json.find("\"", kPos + key.length() + 2);
  if (vStart == std::string::npos)
    return "";
  size_t vEnd = json.find("\"", vStart + 1);
  if (vEnd == std::string::npos)
    return "";
  return json.substr(vStart + 1, vEnd - vStart - 1);
}

// ---------------------------------------------------------------------------
// Helper: extract a JSON bool field value from a flat object.
// ---------------------------------------------------------------------------
static bool JsonBool(const std::string &json, const std::string &key) {
  size_t kPos = json.find("\"" + key + "\":");
  if (kPos == std::string::npos)
    return false;
  size_t vStart = kPos + key.length() + 2;
  while (vStart < json.length() && (json[vStart] == ' ' || json[vStart] == ':'))
    vStart++;
  return json.compare(vStart, 4, "true") == 0;
}

// ---------------------------------------------------------------------------
// SemverGreater: returns true if version string a > b (major.minor.patch).
// Strips a leading 'v' and any pre-release suffix (e.g. "-beta") before
// parsing, so "5.0.0-beta" is treated as "5.0.0". Non-numeric versions
// return false rather than crashing.
// ---------------------------------------------------------------------------
bool UpdateLogic::SemverGreater(const std::string &a, const std::string &b) {
  auto parse = [](const std::string &v, int &maj, int &min, int &pat) -> bool {
    std::string s = v;
    // Strip leading 'v'
    if (!s.empty() && s[0] == 'v')
      s = s.substr(1);
    // Truncate at first non-numeric-dot character (pre-release suffix)
    auto dash = s.find('-');
    if (dash != std::string::npos)
      s = s.substr(0, dash);
    int r = sscanf(s.c_str(), "%d.%d.%d", &maj, &min, &pat);
    return r == 3;
  };
  int aMaj = 0, aMin = 0, aPat = 0;
  int bMaj = 0, bMin = 0, bPat = 0;
  if (!parse(a, aMaj, aMin, aPat))
    return false;
  if (!parse(b, bMaj, bMin, bPat))
    return false;
  if (aMaj != bMaj)
    return aMaj > bMaj;
  if (aMin != bMin)
    return aMin > bMin;
  return aPat > bPat;
}

// ---------------------------------------------------------------------------
// FetchRelease: hits a single GitHub releases endpoint and populates
// a ReleaseInfo from the top-level JSON object.
// ---------------------------------------------------------------------------
ReleaseInfo UpdateLogic::FetchRelease(const std::string &api_path) {
  ReleaseInfo info;
  std::string body = HttpGetGitHub(api_path);
  if (body.empty())
    return info;

  // Find the outermost JSON object
  size_t start = body.find('{');
  if (start == std::string::npos)
    return info;

  // Grab just the top-level object (balanced braces)
  size_t end = std::string::npos;
  int depth = 0;
  for (size_t i = start; i < body.length(); ++i) {
    if (body[i] == '{')
      depth++;
    else if (body[i] == '}')
      depth--;
    if (depth == 0) {
      end = i;
      break;
    }
  }
  if (end == std::string::npos)
    return info;
  std::string obj = body.substr(start, end - start + 1);

  bool isDraft = JsonBool(obj, "draft");
  bool isPrerelease = JsonBool(obj, "prerelease");
  if (isDraft)
    return info;

  std::string tag = JsonString(obj, "tag_name");
  std::string htmlUrl = JsonString(obj, "html_url");
  std::string pubDate = JsonString(obj, "published_at");
  std::string commit = JsonString(obj, "target_commitish");

  if (tag.empty())
    return info;

  // Strip leading 'v' for the version field
  std::string ver = tag;
  if (!ver.empty() && ver[0] == 'v')
    ver = ver.substr(1);

  info.found = true;
  info.version = ver;
  info.release_url = htmlUrl;
  info.publish_date = pubDate;
  info.commit_sha = commit;
  info.is_prerelease = isPrerelease;
  return info;
}

// ---------------------------------------------------------------------------
// NormaliseDate: strips trailing whitespace/CR and normalises the timezone
// suffix so both GitHub's "...Z" and makefile's "...Z" (or "+00:00") compare
// correctly with a plain lexicographic compare.
// ---------------------------------------------------------------------------
static std::string NormaliseDate(const std::string &s) {
  std::string r = s;
  // Trim trailing CR / LF / spaces
  while (!r.empty() &&
         (r.back() == '\r' || r.back() == '\n' || r.back() == ' '))
    r.pop_back();
  // Normalise "+00:00" → "Z" so both formats sort identically
  if (r.size() >= 6 && r.substr(r.size() - 6) == "+00:00")
    r = r.substr(0, r.size() - 6) + "Z";
  return r;
}

// ---------------------------------------------------------------------------
// GetBuildInfo: reads version.txt next to the updater exe (3-line format).
// The updater lives at <root>/Hammer5ToolsUpdater.exe; version.txt is at
// <root>/app/version.txt  — wait, actually the *updater* is at <root>/ and
// version.txt is written into <root>/app/ by makefile.py.  So we try
// root/"app"/version.txt first, then root/"version.txt" as fallback for
// portable/dev layouts.
// Falls back gracefully for old single-line installs and missing lines.
// ---------------------------------------------------------------------------
BuildInfo UpdateLogic::GetBuildInfo() {
  wchar_t buffer[MAX_PATH];
  GetModuleFileNameW(NULL, buffer, MAX_PATH);
  fs::path exeDir = fs::path(buffer).parent_path();

  BuildInfo info;
  info.channel = "stable"; // safe default

  // The updater exe is at <root>\Hammer5ToolsUpdater.exe
  // version.txt is written into <root>\app\version.txt by makefile.py
  fs::path vfPath = exeDir / "app" / "version.txt";
  if (!fs::exists(vfPath)) {
    // Fallback: same folder as the updater (dev / portable layout)
    vfPath = exeDir / "version.txt";
  }

  std::ifstream vf(vfPath);
  if (vf.is_open()) {
    // Line 1: version
    std::string line;
    if (std::getline(vf, line)) {
      // Trim CR/LF
      while (!line.empty() && (line.back() == '\r' || line.back() == '\n'))
        line.pop_back();
      info.version = line;
    }
    // Line 2: channel (optional — old installs only have 1 line)
    if (std::getline(vf, line)) {
      while (!line.empty() && (line.back() == '\r' || line.back() == '\n'))
        line.pop_back();
      if (!line.empty())
        info.channel = line;
    }
    // Line 3: build date (optional)
    if (std::getline(vf, line)) {
      info.build_date = NormaliseDate(line);
    }
  }
  return info;
}

// ---------------------------------------------------------------------------
// CheckForUpdates: channel-aware update check.
//   stable → compare semver against latest stable release.
//   dev    → first check if a new stable is out (higher priority),
//            then compare build date against the rolling "dev" tag.
// ---------------------------------------------------------------------------
ReleaseInfo UpdateLogic::CheckForUpdates(const BuildInfo &local) {
  // Always fetch the latest stable release
  ReleaseInfo stable =
      FetchRelease("/repos/dertwist/Hammer5Tools/releases/latest");

  if (local.channel != "dev") {
    // --- Stable channel ---
    if (stable.found && SemverGreater(stable.version, local.version)) {
      stable.notify_type = NOTIFY_STABLE_AVAILABLE;
      return stable;
    }
  } else {
    // --- Dev channel ---
    // Priority 1: a new stable release is out that supersedes the dev build
    if (stable.found && SemverGreater(stable.version, local.version)) {
      stable.notify_type = NOTIFY_STABLE_FROM_DEV;
      return stable;
    }
    // Priority 2: the rolling "dev" tag has a newer build date.
    // Normalise both timestamps before comparing so format differences
    // ("Z" vs "+00:00") don't cause silent mismatches.
    ReleaseInfo dev =
        FetchRelease("/repos/dertwist/Hammer5Tools/releases/tags/dev");
    if (dev.found && !local.build_date.empty() && !dev.publish_date.empty() &&
        NormaliseDate(dev.publish_date) > local.build_date) {
      dev.notify_type = NOTIFY_DEV_UPDATE;
      return dev;
    }
  }

  return {}; // nothing found, ReleaseInfo.found == false
}

// ---------------------------------------------------------------------------
// Process helpers (retained — used by launcher / other callers)
// ---------------------------------------------------------------------------
void UpdateLogic::KillProcess(const std::wstring &process_name) {
  HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
  if (hSnap == INVALID_HANDLE_VALUE)
    return;

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

bool UpdateLogic::IsProcessRunning(const std::wstring &process_name) {
  bool running = false;
  HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
  if (hSnap == INVALID_HANDLE_VALUE)
    return false;

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
