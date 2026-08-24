#include "request.hpp"

#include <windows.h>

#include <sstream>

namespace launcher
{
namespace
{
std::string Utf8(const std::wstring& value)
{
    if (value.empty())
        return {};
    const auto size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    std::string result(size, '\0');
    WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()), result.data(), size, nullptr, nullptr);
    return result;
}

std::string Escape(const std::string& value)
{
    std::ostringstream result;
    for (const auto character : value)
    {
        switch (character)
        {
            case '\\': result << "\\\\"; break;
            case '"': result << "\\\""; break;
            case '\b': result << "\\b"; break;
            case '\f': result << "\\f"; break;
            case '\n': result << "\\n"; break;
            case '\r': result << "\\r"; break;
            case '\t': result << "\\t"; break;
            default:
                if (static_cast<unsigned char>(character) < 0x20)
                    result << "\\u00" << "0123456789abcdef"[(character >> 4) & 0xf] << "0123456789abcdef"[character & 0xf];
                else
                    result << character;
        }
    }
    return result.str();
}
}

std::wstring QuoteArgument(const std::wstring& argument)
{
    if (argument.find_first_of(L" \t\"") == std::wstring::npos)
        return argument;
    std::wstring result = L"\"";
    std::size_t slashes = 0;
    for (const auto character : argument)
    {
        if (character == L'\\')
        {
            slashes++;
            continue;
        }
        if (character == L'"')
            result.append(slashes * 2 + 1, L'\\');
        else
            result.append(slashes, L'\\');
        slashes = 0;
        result.push_back(character);
    }
    result.append(slashes * 2, L'\\');
    result.push_back(L'"');
    return result;
}

LaunchRequest ParseRequest(const std::vector<std::wstring>& arguments, const std::filesystem::path& workingDirectory)
{
    LaunchRequest request;
    request.WorkingDirectory = workingDirectory;
    request.Arguments = arguments;
    for (std::size_t index = 0; index < arguments.size(); index++)
    {
        const auto& argument = arguments[index];
        const auto consumePath = [&](const std::string& command)
        {
            request.Command = command;
            if (index + 1 < arguments.size())
            {
                auto path = std::filesystem::path(arguments[++index]);
                request.FilePath = (path.is_absolute() ? path : workingDirectory / path).lexically_normal().wstring();
            }
        };
        if (argument == L"--create-vmdl") consumePath("create_vmdl");
        else if (argument == L"--quick-vmdl" || argument == L"--quick-vmdl-dir") consumePath("quick_vmdl");
        else if (argument == L"--quick-batch") consumePath("quick_batch");
        else if (argument == L"--quick-process") consumePath("quick_process");
        else if (argument == L"--quick-process-file") consumePath("quick_process_file");
        else if (!argument.empty() && argument[0] != L'-')
        {
            request.Command = "open_file";
            auto path = std::filesystem::path(argument);
            request.FilePath = (path.is_absolute() ? path : workingDirectory / path).lexically_normal().wstring();
            if (std::filesystem::path(request.FilePath).extension() == L".vsndevts")
                request.EditorType = "soundevent";
        }
    }
    return request;
}

std::string SerializeRequest(const LaunchRequest& request)
{
    std::ostringstream json;
    json << "{\"protocol_version\":1,\"command\":\"" << Escape(request.Command) << "\"";
    if (!request.FilePath.empty())
        json << ",\"file_path\":\"" << Escape(Utf8(request.FilePath)) << "\"";
    json << ",\"editor_type\":\"" << Escape(request.EditorType) << "\"";
    json << ",\"working_directory\":\"" << Escape(Utf8(request.WorkingDirectory.wstring())) << "\"";
    json << ",\"arguments\":[";
    for (std::size_t index = 0; index < request.Arguments.size(); index++)
    {
        if (index > 0) json << ',';
        json << "\"" << Escape(Utf8(request.Arguments[index])) << "\"";
    }
    json << "]}";
    return json.str();
}
}
