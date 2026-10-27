// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

// The report model's JSON (edi ADR-0036): a small value type, a writer and a strict reader (RFC 8259).
// Doubles are written in their shortest round-trip form and read correctly rounded, so a model reads
// back unchanged; a non-finite double is written as null. The writer escapes <, >, & and U+2028/U+2029
// as \uXXXX, so its output can sit inside an HTML <script> element as it is.

namespace edi::json {

struct Value;
using Array = std::vector<Value>;
// Members in the order they were added; a reader keeps the file's order.
using Object = std::vector<std::pair<std::string, Value>>;

struct Value {
    std::variant<std::nullptr_t, bool, double, std::string, Array, Object> data = nullptr;

    Value() = default;
    Value(std::nullptr_t) {}
    Value(bool flag) : data(flag) {}
    Value(double number) : data(number) {}
    Value(int number) : data(static_cast<double>(number)) {}
    Value(const char* text) : data(std::string(text)) {}
    Value(std::string text) : data(std::move(text)) {}
    Value(Array items) : data(std::move(items)) {}
    Value(Object members) : data(std::move(members)) {}

    bool is_null() const { return std::holds_alternative<std::nullptr_t>(data); }
    // The typed accessors throw std::invalid_argument naming `what` when the value has another type.
    bool boolean(const char* what) const;
    double number(const char* what) const;  // null reads as NaN
    const std::string& string(const char* what) const;
    const Array& array(const char* what) const;
    const Object& object(const char* what) const;
    // A member of an object; throws when it is missing.
    const Value& at(const std::string& key) const;
    // A member of an object, or null when it is missing.
    const Value& get(const std::string& key) const;
};

std::string write(const Value& value);
std::uint64_t encoded_size(const Value& value, std::uint64_t limit = UINT64_MAX);
// Same writer byte rules, borrowing string bytes for pre-copy admission.
std::uint64_t encoded_string_size(std::string_view text, std::uint64_t limit = UINT64_MAX);
Value parse(const std::string& text);

}  // namespace edi::json
