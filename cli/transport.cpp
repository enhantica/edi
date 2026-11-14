// SPDX-License-Identifier: BSD-3-Clause
#include "transport.hpp"

#include <cstddef>
#include <string>

#if defined(_WIN32)
#include "windows_sdk.hpp"
#include <winhttp.h>
#else
#include <dlfcn.h>
#endif

namespace edi_cli {
namespace {

bool is_web(const std::string& url) { return url.rfind("http://", 0) == 0 || url.rfind("https://", 0) == 0; }

edi::online::Reply answered(long status, std::string bytes, const std::string& url) {
    if (status >= 200 && status < 300) return {true, std::move(bytes), {}, false};
    // A server error is an outage, after which the next location is tried; any other status is an answer.
    return {false, {}, url + " answered " + std::to_string(status), status >= 500};
}

#if defined(_WIN32)

struct Handle {
    HINTERNET value = nullptr;
    ~Handle() {
        if (value != nullptr) WinHttpCloseHandle(value);
    }
};

std::wstring wide(const std::string& text) {
    if (text.empty()) return {};
    const int size = MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), nullptr, 0);
    std::wstring out(static_cast<std::size_t>(size), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), out.data(), size);
    return out;
}

edi::online::Reply failed(const std::string& url) {
    return {false, {}, url + ": the connection failed (Windows error " + std::to_string(GetLastError()) + ")", true};
}

edi::online::Reply web(const std::string& url) {
    const std::wstring address = wide(url);
    URL_COMPONENTS parts{};
    parts.dwStructSize = sizeof(parts);
    parts.dwHostNameLength = static_cast<DWORD>(-1);
    parts.dwUrlPathLength = static_cast<DWORD>(-1);
    parts.dwExtraInfoLength = static_cast<DWORD>(-1);
    if (!WinHttpCrackUrl(address.c_str(), 0, 0, &parts)) return {false, {}, url + " is not a URL", false};
    const std::wstring host(parts.lpszHostName, parts.dwHostNameLength);
    std::wstring path(parts.lpszUrlPath, parts.dwUrlPathLength);
    path.append(parts.lpszExtraInfo, parts.dwExtraInfoLength);
    Handle session{WinHttpOpen(L"edi", WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, WINHTTP_NO_PROXY_NAME,
                               WINHTTP_NO_PROXY_BYPASS, 0)};
    if (session.value == nullptr) return failed(url);
    WinHttpSetTimeouts(session.value, 30000, 30000, 30000, 30000);
    Handle connection{WinHttpConnect(session.value, host.c_str(), parts.nPort, 0)};
    if (connection.value == nullptr) return failed(url);
    const DWORD secure = parts.nScheme == INTERNET_SCHEME_HTTPS ? WINHTTP_FLAG_SECURE : 0;
    Handle request{WinHttpOpenRequest(connection.value, L"GET", path.c_str(), nullptr, WINHTTP_NO_REFERER,
                                      WINHTTP_DEFAULT_ACCEPT_TYPES, secure)};
    if (request.value == nullptr) return failed(url);
    if (!WinHttpSendRequest(request.value, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse(request.value, nullptr))
        return failed(url);
    DWORD status = 0;
    DWORD size = sizeof(status);
    if (!WinHttpQueryHeaders(request.value, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &status, &size, WINHTTP_NO_HEADER_INDEX))
        return failed(url);
    std::string bytes;
    for (;;) {
        DWORD available = 0;
        if (!WinHttpQueryDataAvailable(request.value, &available)) return failed(url);
        if (available == 0) break;
        const std::size_t start = bytes.size();
        bytes.resize(start + available);
        DWORD read = 0;
        if (!WinHttpReadData(request.value, bytes.data() + start, available, &read)) return failed(url);
        bytes.resize(start + read);
    }
    return answered(static_cast<long>(status), std::move(bytes), url);
}

bool web_ready(std::string&) { return true; }

#else

// libcurl is loaded when a download first needs it, so the CLI itself does not depend on it and a system without it
// can still fit projects. Only libcurl's stable C interface is used; its option numbers are part of that interface.
struct Curl {
    void* library = nullptr;
    void* (*easy_init)() = nullptr;
    int (*easy_setopt)(void*, int, ...) = nullptr;
    int (*easy_perform)(void*) = nullptr;
    int (*easy_getinfo)(void*, int, ...) = nullptr;
    void (*easy_cleanup)(void*) = nullptr;
    const char* (*easy_strerror)(int) = nullptr;
    int (*global_init)(long) = nullptr;
};

constexpr int kUrl = 10002, kWriteFunction = 20011, kWriteData = 10001, kFollowLocation = 52, kConnectTimeout = 78,
              kTimeout = 13, kNoSignal = 99, kUserAgent = 10018, kResponseCode = 0x200002;

template <typename Function>
bool symbol(void* library, const char* name, Function& target) {
    target = reinterpret_cast<Function>(dlsym(library, name));
    return target != nullptr;
}

const Curl* curl() {
    static const Curl loaded = [] {
        Curl c;
#if defined(__APPLE__)
        const char* names[] = {"/usr/lib/libcurl.4.dylib", "libcurl.4.dylib", "libcurl.dylib"};
#else
        const char* names[] = {"libcurl.so.4", "libcurl-gnutls.so.4", "libcurl.so"};
#endif
        for (const char* name : names) {
            if ((c.library = dlopen(name, RTLD_NOW | RTLD_LOCAL)) != nullptr) break;
        }
        if (c.library == nullptr || !symbol(c.library, "curl_easy_init", c.easy_init) ||
            !symbol(c.library, "curl_easy_setopt", c.easy_setopt) ||
            !symbol(c.library, "curl_easy_perform", c.easy_perform) ||
            !symbol(c.library, "curl_easy_getinfo", c.easy_getinfo) ||
            !symbol(c.library, "curl_easy_cleanup", c.easy_cleanup) ||
            !symbol(c.library, "curl_easy_strerror", c.easy_strerror) ||
            !symbol(c.library, "curl_global_init", c.global_init)) {
            c.library = nullptr;
            return c;
        }
        c.global_init(3);  // CURL_GLOBAL_DEFAULT
        return c;
    }();
    return loaded.library != nullptr ? &loaded : nullptr;
}

bool web_ready(std::string& why);

std::size_t collect(char* data, std::size_t size, std::size_t count, void* target) {
    static_cast<std::string*>(target)->append(data, size * count);
    return size * count;
}

edi::online::Reply web(const std::string& url) {
    const Curl* c = curl();
    if (c == nullptr) {
        std::string why;
        web_ready(why);
        return {false, {}, why, true};
    }
    void* handle = c->easy_init();
    if (handle == nullptr) return {false, {}, url + ": libcurl could not start a transfer", true};
    std::string bytes;
    c->easy_setopt(handle, kUrl, url.c_str());
    c->easy_setopt(handle, kWriteFunction, &collect);
    c->easy_setopt(handle, kWriteData, &bytes);
    c->easy_setopt(handle, kFollowLocation, 1L);
    c->easy_setopt(handle, kConnectTimeout, 30L);
    c->easy_setopt(handle, kTimeout, 300L);
    c->easy_setopt(handle, kNoSignal, 1L);
    c->easy_setopt(handle, kUserAgent, "edi");
    const int code = c->easy_perform(handle);
    long status = 0;
    if (code == 0) c->easy_getinfo(handle, kResponseCode, &status);
    c->easy_cleanup(handle);
    // Any transfer failure (no network, no host, a timeout, a broken TLS handshake) is an outage.
    if (code != 0) return {false, {}, url + ": " + c->easy_strerror(code), true};
    return answered(status, std::move(bytes), url);
}

bool web_ready(std::string& why) {
    if (curl() != nullptr) return true;
#if defined(__APPLE__)
    why = "Downloads from the web need libcurl, which macOS normally provides; it could not be loaded.";
#else
    why = "Downloads from the web need libcurl, which this system does not have. Install it (for example the "
          "libcurl4 package), or use a folder with --source.";
#endif
    return false;
}

#endif

}  // namespace

edi::online::Reply fetch(const std::string& url) {
    return is_web(url) ? web(url) : edi::online::read_local(url);
}

bool web_available(std::string& why) { return web_ready(why); }

}  // namespace edi_cli
