// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <algorithm>
#include <charconv>
#include <cmath>
#include <set>
#include <stdexcept>
#include <string_view>

#include "edi/assistant.hpp"
#include "json.hpp"

namespace edi::assistant::detail {
using J = json::Value;
using O = json::Object;
using A = json::Array;
inline constexpr std::size_t kMessageLimit = Limits::message_bytes;

struct Refusal : std::runtime_error {
    std::string code;
    Refusal(std::string kind, std::string message) : std::runtime_error(std::move(message)), code(std::move(kind)) {}
};
[[noreturn]] inline void refuse(const std::string& code, const std::string& message) {
    throw Refusal(code, message);
}
inline Reply success(J value = O{}) { return {true, {}, json::write(value)}; }
inline Reply failure(const std::string& code, const std::string& message) {
    std::string safe;
    for (unsigned char c : message) {
        if (safe.size() >= Limits::error_bytes) break;
        if (c >= 32 && c != 127) safe.push_back(static_cast<char>(c));
    }
    while (!safe.empty() && static_cast<unsigned char>(safe.back()) >= 0x80) safe.pop_back();
    return {false, "edi.assistant." + code, json::write(O{{"message", safe}})};
}
inline bool has(const J& value, const std::string& key) {
    for (const auto& [name, item] : value.object("object")) {
        (void)item;
        if (name == key) return true;
    }
    return false;
}
inline void shape(const J& value, std::initializer_list<const char*> required,
                  std::initializer_list<const char*> optional = {}) {
    std::set<std::string> seen;
    for (const auto& [key, item] : value.object("object")) {
        (void)item;
        if (!seen.insert(key).second) refuse("invalid_argument", "Duplicate field: " + key);
        const auto matches = [&](const char* name) { return key == name; };
        if (std::none_of(required.begin(), required.end(), matches) &&
            std::none_of(optional.begin(), optional.end(), matches)) refuse("invalid_argument", "Unknown field: " + key);
    }
    for (const char* name : required) if (!seen.count(name)) refuse("invalid_argument", "Missing field: " + std::string(name));
}
inline void unique(const J& value) {
    if (const auto* object = std::get_if<O>(&value.data)) {
        std::set<std::string> names;
        for (const auto& [name, item] : *object) {
            if (!names.insert(name).second) refuse("invalid_json", "Duplicate JSON member: " + name);
            unique(item);
        }
    } else if (const auto* array = std::get_if<A>(&value.data)) for (const J& item : *array) unique(item);
}
inline bool utf8(std::string_view text) {
    for (std::size_t i = 0; i < text.size();) {
        const auto c = static_cast<unsigned char>(text[i++]);
        if (c < 0x80) continue;
        unsigned n = 0;
        std::uint32_t code = 0, minimum = 0;
        if (c >= 0xc2 && c <= 0xdf) { n = 1; code = c & 31; minimum = 0x80; }
        else if (c >= 0xe0 && c <= 0xef) { n = 2; code = c & 15; minimum = 0x800; }
        else if (c >= 0xf0 && c <= 0xf4) { n = 3; code = c & 7; minimum = 0x10000; }
        else return false;
        if (text.size() - i < n) return false;
        while (n--) {
            const auto next = static_cast<unsigned char>(text[i++]);
            if ((next & 0xc0) != 0x80) return false;
            code = (code << 6) | (next & 63);
        }
        if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff)) return false;
    }
    return true;
}
inline J parse(const std::string& text, std::uint64_t limit = Limits::message_bytes) {
    if (text.size() > limit || !utf8(text)) refuse("invalid_json", "Invalid UTF-8 or oversized message");
    std::uint64_t depth = 0;
    bool quoted = false, escaped = false;
    for (char c : text) {
        if (quoted) { if (escaped) escaped = false; else if (c == '\\') escaped = true; else if (c == '"') quoted = false; }
        else if (c == '"') quoted = true;
        else if (c == '{' || c == '[') { if (++depth > Limits::json_depth) refuse("invalid_json", "JSON nesting limit exceeded"); }
        else if ((c == '}' || c == ']') && depth) --depth;
    }
    try { J result = json::parse(text); unique(result); return result; }
    catch (const Refusal&) { throw; }
    catch (const std::exception& error) { refuse("invalid_json", error.what()); }
}
inline J canonical(J value) {
    if (auto* object = std::get_if<O>(&value.data)) {
        for (auto& member : *object) member.second = canonical(std::move(member.second));
        std::sort(object->begin(), object->end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    } else if (auto* array = std::get_if<A>(&value.data)) for (auto& item : *array) item = canonical(std::move(item));
    return value;
}
inline std::uint64_t payload_size(const J& value, std::uint64_t limit = UINT64_MAX) {
    try { return json::encoded_size(value, limit); }
    catch (const std::length_error&) { refuse("resource_exhausted", "Assistant payload limit exceeded"); }
}

inline void bounded(const J& value, std::uint64_t bytes, std::uint64_t count = UINT64_MAX) {
    if (const auto* array = std::get_if<A>(&value.data); array && array->size() > count)
        refuse("resource_exhausted", "Assistant collection count limit exceeded");
    try { (void)json::encoded_size(value, bytes); }
    catch (const std::length_error&) { refuse("resource_exhausted", "Assistant payload limit exceeded"); }
}

inline std::string string(const J& value, const char* name, bool empty = false) {
    const auto result = value.at(name).string(name);
    const std::string key(name);
    if ((key.ends_with("_id") || key == "model" || key == "effort") && result.size() > Limits::id_bytes)
        refuse("resource_exhausted", "Assistant identifier exceeds limit");
    if (!empty && result.empty()) refuse("invalid_argument", std::string(name) + " is empty");
    return result;
}
inline double number(const J& value, const char* name) {
    const double result = value.at(name).number(name);
    if (!std::isfinite(result)) refuse("invalid_argument", std::string(name) + " must be finite");
    return result;
}
inline std::uint64_t positive(const J& value, const char* name) {
    const double result = number(value, name);
    if (result <= 0 || result > 9007199254740991.0 || std::floor(result) != result)
        refuse("invalid_argument", std::string(name) + " must be a positive safe integer");
    return static_cast<std::uint64_t>(result);
}
inline std::uint64_t revision(const J& value) {
    const auto text = string(value, "revision");
    std::uint64_t result = 0;
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), result);
    if (error != std::errc{} || end != text.data() + text.size() ||
        !std::all_of(text.begin(), text.end(), [](char c) { return c >= '0' && c <= '9'; }))
        refuse("invalid_argument", "revision must be an unsigned decimal string");
    return result;
}
inline void envelope(const J& value) {
    if (string(value, "schema") != "edi.assistant/1") refuse("invalid_schema", "Unsupported assistant schema");
}
inline void set(J& value, const std::string& key, J item) {
    auto& members = std::get<O>(value.data);
    for (auto& [name, old] : members) if (name == key) { old = std::move(item); return; }
    members.emplace_back(key, std::move(item));
}
}  // namespace edi::assistant::detail
