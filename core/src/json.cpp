// SPDX-License-Identifier: BSD-3-Clause
#include "json.hpp"

#include <charconv>
#include <clocale>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <stdexcept>

namespace edi::json {

namespace {

[[noreturn]] void fail(const char* what, const char* expected) {
    throw std::invalid_argument(std::string("report JSON: ") + what + " is not " + expected);
}

struct SizeCounter {
    std::uint64_t size = 0, limit;
    void count(std::uint64_t n) {
        if (n > limit - size) throw std::length_error("JSON encoded size limit exceeded");
        size += n;
    }
    void operator+=(char) { count(1); }
    void operator+=(const char* text) { count(std::char_traits<char>::length(text)); }
    void operator+=(const std::string& text) { count(text.size()); }
    void append(const char* begin, const char* end) { count(static_cast<std::uint64_t>(end - begin)); }
};

void append_utf8(std::string& out, std::uint32_t code) {
    if (code < 0x80) {
        out += static_cast<char>(code);
    } else if (code < 0x800) {
        out += static_cast<char>(0xC0 | (code >> 6));
        out += static_cast<char>(0x80 | (code & 0x3F));
    } else if (code < 0x10000) {
        out += static_cast<char>(0xE0 | (code >> 12));
        out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (code & 0x3F));
    } else {
        out += static_cast<char>(0xF0 | (code >> 18));
        out += static_cast<char>(0x80 | ((code >> 12) & 0x3F));
        out += static_cast<char>(0x80 | ((code >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (code & 0x3F));
    }
}

template <typename Output>
void write_escaped(Output& out, std::string_view text) {
    static const char* const hex = "0123456789abcdef";
    out += '"';
    for (std::size_t i = 0; i < text.size(); ++i) {
        const auto byte = static_cast<unsigned char>(text[i]);
        // U+2028 and U+2029 (E2 80 A8, E2 80 A9) end a line in older JavaScript; < > & keep the text inert
        // inside an HTML <script> element.
        if (byte == 0xE2 && i + 2 < text.size() && static_cast<unsigned char>(text[i + 1]) == 0x80 &&
            (static_cast<unsigned char>(text[i + 2]) == 0xA8 || static_cast<unsigned char>(text[i + 2]) == 0xA9)) {
            out += static_cast<unsigned char>(text[i + 2]) == 0xA8 ? "\\u2028" : "\\u2029";
            i += 2;
            continue;
        }
        switch (byte) {
            case '"':
                out += "\\\"";
                break;
            case '\\':
                out += "\\\\";
                break;
            case '\n':
                out += "\\n";
                break;
            case '\r':
                out += "\\r";
                break;
            case '\t':
                out += "\\t";
                break;
            case '<':
            case '>':
            case '&':
                out += "\\u00";
                out += hex[byte >> 4];
                out += hex[byte & 0xF];
                break;
            default:
                if (byte < 0x20) {
                    out += "\\u00";
                    out += hex[byte >> 4];
                    out += hex[byte & 0xF];
                } else {
                    out += static_cast<char>(byte);
                }
        }
    }
    out += '"';
}

template <typename Output>
void write_value(Output& out, const Value& value) {
    if (value.is_null()) {
        out += "null";
    } else if (const bool* flag = std::get_if<bool>(&value.data)) {
        out += *flag ? "true" : "false";
    } else if (const double* number = std::get_if<double>(&value.data)) {
        if (!std::isfinite(*number)) {
            out += "null";
        } else if (*number == 0.0 && std::signbit(*number)) {
            out += "-0.0";  // "-0" would read back as the integer 0 in a reader that tells integers from floats
        } else {
            char buffer[64];
            const auto result = std::to_chars(buffer, buffer + sizeof(buffer), *number);
            out.append(buffer, result.ptr);
        }
    } else if (const std::string* text = std::get_if<std::string>(&value.data)) {
        write_escaped(out, *text);
    } else if (const Array* items = std::get_if<Array>(&value.data)) {
        out += '[';
        for (std::size_t i = 0; i < items->size(); ++i) {
            if (i > 0) {
                out += ',';
            }
            write_value(out, (*items)[i]);
        }
        out += ']';
    } else {
        const Object& members = std::get<Object>(value.data);
        out += '{';
        for (std::size_t i = 0; i < members.size(); ++i) {
            if (i > 0) {
                out += ',';
            }
            write_escaped(out, members[i].first);
            out += ':';
            write_value(out, members[i].second);
        }
        out += '}';
    }
}

class Reader {
   public:
    explicit Reader(const std::string& text) : text_(text) {}

    Value document() {
        Value value = read_value(0);
        skip_space();
        if (at_ != text_.size()) {
            error("text after the value");
        }
        return value;
    }

   private:
    static constexpr int kMaxDepth = 256;
    const std::string& text_;
    std::size_t at_ = 0;

    [[noreturn]] void error(const std::string& what) const {
        throw std::invalid_argument("report JSON: " + what + " at offset " + std::to_string(at_));
    }

    void skip_space() {
        while (at_ < text_.size() &&
               (text_[at_] == ' ' || text_[at_] == '\t' || text_[at_] == '\n' || text_[at_] == '\r')) {
            ++at_;
        }
    }

    bool take(const char* word) {
        const std::string expected(word);
        if (text_.compare(at_, expected.size(), expected) == 0) {
            at_ += expected.size();
            return true;
        }
        return false;
    }

    Value read_value(int depth) {
        if (depth > kMaxDepth) {
            error("nesting too deep");
        }
        skip_space();
        if (at_ >= text_.size()) {
            error("missing value");
        }
        const char next = text_[at_];
        if (next == '{') {
            return read_object(depth);
        }
        if (next == '[') {
            return read_array(depth);
        }
        if (next == '"') {
            return read_string();
        }
        if (take("null")) {
            return nullptr;
        }
        if (take("true")) {
            return true;
        }
        if (take("false")) {
            return false;
        }
        return read_number();
    }

    Value read_object(int depth) {
        ++at_;
        Object members;
        skip_space();
        if (at_ < text_.size() && text_[at_] == '}') {
            ++at_;
            return members;
        }
        while (true) {
            skip_space();
            if (at_ >= text_.size() || text_[at_] != '"') {
                error("expected a member name");
            }
            std::string key = read_string().string("member name");
            skip_space();
            if (at_ >= text_.size() || text_[at_] != ':') {
                error("expected ':'");
            }
            ++at_;
            members.emplace_back(std::move(key), read_value(depth + 1));
            skip_space();
            if (at_ < text_.size() && text_[at_] == ',') {
                ++at_;
                continue;
            }
            if (at_ < text_.size() && text_[at_] == '}') {
                ++at_;
                return members;
            }
            error("expected ',' or '}'");
        }
    }

    Value read_array(int depth) {
        ++at_;
        Array items;
        skip_space();
        if (at_ < text_.size() && text_[at_] == ']') {
            ++at_;
            return items;
        }
        while (true) {
            items.push_back(read_value(depth + 1));
            skip_space();
            if (at_ < text_.size() && text_[at_] == ',') {
                ++at_;
                continue;
            }
            if (at_ < text_.size() && text_[at_] == ']') {
                ++at_;
                return items;
            }
            error("expected ',' or ']'");
        }
    }

    std::uint32_t read_hex4() {
        if (at_ + 4 > text_.size()) {
            error("short \\u escape");
        }
        std::uint32_t code = 0;
        for (int i = 0; i < 4; ++i) {
            const char digit = text_[at_++];
            code <<= 4;
            if (digit >= '0' && digit <= '9') {
                code |= static_cast<std::uint32_t>(digit - '0');
            } else if (digit >= 'a' && digit <= 'f') {
                code |= static_cast<std::uint32_t>(digit - 'a' + 10);
            } else if (digit >= 'A' && digit <= 'F') {
                code |= static_cast<std::uint32_t>(digit - 'A' + 10);
            } else {
                error("bad \\u escape");
            }
        }
        return code;
    }

    Value read_string() {
        ++at_;
        std::string out;
        while (true) {
            if (at_ >= text_.size()) {
                error("unterminated string");
            }
            const auto byte = static_cast<unsigned char>(text_[at_++]);
            if (byte == '"') {
                return out;
            }
            if (byte < 0x20) {
                error("control character in a string");
            }
            if (byte != '\\') {
                out += static_cast<char>(byte);
                continue;
            }
            if (at_ >= text_.size()) {
                error("unterminated escape");
            }
            const char escape = text_[at_++];
            switch (escape) {
                case '"':
                case '\\':
                case '/':
                    out += escape;
                    break;
                case 'b':
                    out += '\b';
                    break;
                case 'f':
                    out += '\f';
                    break;
                case 'n':
                    out += '\n';
                    break;
                case 'r':
                    out += '\r';
                    break;
                case 't':
                    out += '\t';
                    break;
                case 'u': {
                    std::uint32_t code = read_hex4();
                    if (code >= 0xD800 && code <= 0xDBFF) {
                        if (!take("\\u")) {
                            error("unpaired surrogate");
                        }
                        const std::uint32_t low = read_hex4();
                        if (low < 0xDC00 || low > 0xDFFF) {
                            error("unpaired surrogate");
                        }
                        code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00);
                    } else if (code >= 0xDC00 && code <= 0xDFFF) {
                        error("unpaired surrogate");
                    }
                    append_utf8(out, code);
                    break;
                }
                default:
                    error("bad escape");
            }
        }
    }

    Value read_number() {
        const std::size_t start = at_;
        if (at_ < text_.size() && text_[at_] == '-') {
            ++at_;
        }
        const auto digits = [this] {
            const std::size_t begin = at_;
            while (at_ < text_.size() && text_[at_] >= '0' && text_[at_] <= '9') {
                ++at_;
            }
            return at_ - begin;
        };
        const std::size_t integer_start = at_;
        if (digits() == 0 || (text_[integer_start] == '0' && at_ - integer_start > 1)) {
            at_ = start;
            error("bad number");
        }
        if (at_ < text_.size() && text_[at_] == '.') {
            ++at_;
            if (digits() == 0) {
                error("bad number");
            }
        }
        if (at_ < text_.size() && (text_[at_] == 'e' || text_[at_] == 'E')) {
            ++at_;
            if (at_ < text_.size() && (text_[at_] == '+' || text_[at_] == '-')) {
                ++at_;
            }
            if (digits() == 0) {
                error("bad number");
            }
        }
        // strtod reads the locale's radix character, so the '.' is swapped for it.
        std::string number = text_.substr(start, at_ - start);
        const char* radix = std::localeconv()->decimal_point;
        if (radix != nullptr && radix[0] != '\0' && (radix[0] != '.' || radix[1] != '\0')) {
            const std::size_t dot = number.find('.');
            if (dot != std::string::npos) {
                number.replace(dot, 1, radix);
            }
        }
        char* end = nullptr;
        const double value = std::strtod(number.c_str(), &end);
        if (end != number.c_str() + number.size() || !std::isfinite(value)) {
            error("number out of range");
        }
        return value;
    }
};

}  // namespace

bool Value::boolean(const char* what) const {
    const bool* flag = std::get_if<bool>(&data);
    if (flag == nullptr) {
        fail(what, "a boolean");
    }
    return *flag;
}

double Value::number(const char* what) const {
    if (is_null()) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    const double* value = std::get_if<double>(&data);
    if (value == nullptr) {
        fail(what, "a number");
    }
    return *value;
}

const std::string& Value::string(const char* what) const {
    const std::string* text = std::get_if<std::string>(&data);
    if (text == nullptr) {
        fail(what, "a string");
    }
    return *text;
}

const Array& Value::array(const char* what) const {
    const Array* items = std::get_if<Array>(&data);
    if (items == nullptr) {
        fail(what, "an array");
    }
    return *items;
}

const Object& Value::object(const char* what) const {
    const Object* members = std::get_if<Object>(&data);
    if (members == nullptr) {
        fail(what, "an object");
    }
    return *members;
}

const Value& Value::at(const std::string& key) const {
    for (const auto& [name, value] : object(key.c_str())) {
        if (name == key) {
            return value;
        }
    }
    throw std::invalid_argument("report JSON: no member '" + key + "'");
}

const Value& Value::get(const std::string& key) const {
    static const Value missing;
    for (const auto& [name, value] : object(key.c_str())) {
        if (name == key) {
            return value;
        }
    }
    return missing;
}

std::uint64_t encoded_string_size(std::string_view text, std::uint64_t limit) {
    SizeCounter counter{0, limit};
    write_escaped(counter, text);
    return counter.size;
}

std::uint64_t encoded_size(const Value& value, std::uint64_t limit) {
    SizeCounter counter{0, limit};
    write_value(counter, value);
    return counter.size;
}

std::string write(const Value& value) {
    std::string out;
    write_value(out, value);
    return out;
}

Value parse(const std::string& text) { return Reader(text).document(); }

}  // namespace edi::json
