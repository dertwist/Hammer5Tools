#include "request.hpp"

#include <cassert>

int main()
{
    assert(launcher::QuoteArgument(L"plain") == L"plain");
    assert(launcher::QuoteArgument(L"two words") == L"\"two words\"");
    const auto request = launcher::ParseRequest({L"--quick-vmdl", L"folder with spaces"}, L"C:\\work");
    assert(request.Command == "quick_vmdl");
    assert(request.FilePath == L"C:\\work\\folder with spaces");
    const auto json = launcher::SerializeRequest(request);
    assert(json.find("\"protocol_version\":1") != std::string::npos);
    assert(json.find("folder with spaces") != std::string::npos);
    const auto openRequest = launcher::ParseRequest({L"events\\addon.vsndevts"}, L"C:\\work");
    assert(openRequest.Command == "open_file");
    assert(openRequest.EditorType == "soundevent");
    assert(openRequest.FilePath == L"C:\\work\\events\\addon.vsndevts");
    return 0;
}
