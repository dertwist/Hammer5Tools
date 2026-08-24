#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace launcher
{
struct LaunchRequest
{
    std::string Command = "show";
    std::wstring FilePath;
    std::string EditorType = "smartprop";
    std::filesystem::path WorkingDirectory;
    std::vector<std::wstring> Arguments;
};

std::wstring QuoteArgument(const std::wstring& argument);
std::string SerializeRequest(const LaunchRequest& request);
LaunchRequest ParseRequest(const std::vector<std::wstring>& arguments, const std::filesystem::path& workingDirectory);
}
