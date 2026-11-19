// SPDX-License-Identifier: BSD-3-Clause
#include "gpx_records.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

namespace edi::gpx {
namespace {
std::int64_t decimal(std::string_view line) {
    if (line.ends_with('L')) line.remove_suffix(1);
    std::int64_t result{};
    const auto end = line.data() + line.size();
    const auto parsed = std::from_chars(line.data(), end, result);
    require(parsed.ec == std::errc{} && parsed.ptr == end, "invalid GPX integer");
    return result;
}

std::uint64_t bits(std::string_view bytes, bool little_endian) {
    std::uint64_t value{};
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        const auto index = little_endian ? bytes.size() - 1 - i : i;
        value = (value << 8U) | static_cast<std::uint8_t>(bytes[index]);
    }
    return value;
}

std::string latin1(std::string_view text) {
    std::string bytes;
    bytes.reserve(text.size());
    for (std::size_t i = 0; i < text.size(); ++i) {
        const auto first = static_cast<std::uint8_t>(text[i]);
        if (first < 128) {
            bytes += text[i];
        } else {
            require((first == 194 || first == 195) && i + 1 < text.size(),
                    "invalid Latin-1 payload in GPX");
            const auto second = static_cast<std::uint8_t>(text[++i]);
            require((second & 192U) == 128U, "invalid Latin-1 continuation in GPX");
            bytes += static_cast<char>(((first & 3U) << 6U) | (second & 63U));
        }
    }
    return bytes;
}
}  // namespace

std::string_view Records::take(std::size_t count) {
    require(count <= input_.size() - offset_, "truncated GPX record");
    const auto part = input_.substr(offset_, count);
    offset_ += count;
    return part;
}

std::string_view Records::line() {
    const auto end = input_.find('\n', offset_);
    require(end != std::string_view::npos, "unterminated GPX record");
    const auto part = take(end - offset_);
    take(1);
    return part;
}

std::uint32_t Records::little(std::size_t width) {
    return static_cast<std::uint32_t>(bits(take(width), true));
}

Id Records::top() const {
    require(!stack_.empty() && stack_.back() != marker, "invalid GPX stack");
    return stack_.back();
}

Id Records::pop() {
    const Id id = top();
    stack_.pop_back();
    return id;
}

Sequence Records::marked() {
    const auto mark = std::find(stack_.rbegin(), stack_.rend(), marker);
    require(mark != stack_.rend(), "missing GPX stack delimiter");
    Sequence items(mark.base(), stack_.end());
    stack_.erase(mark.base() - 1, stack_.end());
    return items;
}

void Records::push(Id id) {
    require(stack_.size() < max_items, "GPX stack is too large");
    stack_.push_back(id);
}

void Records::add(Value value) {
    require(nodes_.size() < max_items, "GPX object count is too large");
    push(nodes_.size());
    nodes_.push_back(std::move(value));
}

void Records::extend(Sequence items, bool dict) {
    auto& value = nodes_.at(top());
    Sequence* children = nullptr;
    if (dict) {
        if (auto* table = std::get_if<Dictionary>(&value)) children = &table->pairs;
    } else {
        children = std::get_if<Sequence>(&value);
    }
    require(children != nullptr && items.size() <= max_items - children->size() &&
                (!dict || items.size() % 2 == 0),
            "invalid GPX container");
    children->insert(children->end(), items.begin(), items.end());
}

void Records::set_memo(std::uint32_t slot) {
    require(memo_.size() < max_items, "GPX memo is too large");
    memo_[slot] = top();
}

void Records::get_memo(std::uint32_t slot) {
    const auto item = memo_.find(slot);
    require(item != memo_.end(), "invalid GPX memo reference");
    push(item->second);
}

void Records::read_global() {
    const auto module = line();
    const auto name = line();
    if (module == "numpy" && name == "ndarray")
        add(Factory::Array);
    else if (module == "numpy" && name == "dtype")
        add(Factory::Dtype);
    else if ((module == "numpy._core.multiarray" || module == "numpy.core.multiarray") &&
             name == "_reconstruct")
        add(Factory::Reconstruct);
    else if ((module == "numpy._core.multiarray" || module == "numpy.core.multiarray") &&
             name == "scalar")
        add(Factory::Scalar);
    else if (module == "_codecs" && name == "encode")
        add(Factory::Encode);
    else
        refuse("GPX contains an unsupported serialized object");
}

void Records::reduce() {
    const auto& arguments = sequence(pop());
    const auto factory = as<Factory>(pop(), "built-in data layout");
    switch (factory) {
        case Factory::Dtype: {
            require(!arguments.empty(), "missing GPX dtype");
            const auto& type = text(arguments.front());
            require(type == "f8" || type == "f4" || type == "i8" || type == "i4" || type == "i2" ||
                        type == "i1" || type == "u1" || type == "b1",
                    "unsupported GPX dtype");
            add(Dtype{type[0], static_cast<std::size_t>(type[1] - '0')});
            break;
        }
        case Factory::Reconstruct:
            require(arguments.size() == 3 &&
                        as<Factory>(arguments[0], "array token") == Factory::Array,
                    "invalid GPX array constructor");
            add(Array{Dtype{'b', 1}, {}, marker});
            break;
        case Factory::Scalar:
            require(arguments.size() == 2, "invalid GPX scalar");
            add(element(Array{as<Dtype>(arguments[0], "dtype"), {1}, arguments[1]}, 0));
            break;
        case Factory::Encode: {
            require(arguments.size() == 2 && text(arguments[1]) == "latin1",
                    "unsupported GPX byte encoding");
            const auto& encoded = text(arguments[0]);
            require(encoded.size() <= input_.size() - decoded_bytes_, "GPX byte budget exceeded");
            decoded_bytes_ += encoded.size();
            add(Bytes{latin1(encoded)});
            break;
        }
        case Factory::Array:
            refuse("unexpected GPX array operation");
    }
}

void Records::build() {
    const auto& state = sequence(pop());
    auto& target = nodes_.at(top());
    if (auto* dtype = std::get_if<Dtype>(&target)) {
        require(state.size() == 8 && none(state[2]) && none(state[3]) && none(state[4]),
                "unsupported GPX dtype state");
        const auto& endian = text(state[1]);
        require(endian == "<" || endian == ">" || (endian == "|" && dtype->width == 1),
                "unsupported GPX byte order");
        dtype->endian = endian.front();
        return;
    }
    auto* output = std::get_if<Array>(&target);
    require(output != nullptr && state.size() == 5 && !truth(state[3]),
            "unsupported GPX array state");
    const auto dtype = as<Dtype>(state[2], "dtype");
    const auto& bytes = as<Bytes>(state[4], "array bytes").value;
    std::vector<std::size_t> shape;
    std::size_t size = dtype.width;
    for (const auto axis : sequence(state[1])) {
        const auto length = as<std::int64_t>(axis, "array dimension");
        require(
            length >= 0 && length <= static_cast<std::int64_t>(input_.size()) && shape.size() < 4,
            "invalid GPX array dimension");
        const auto extent = static_cast<std::size_t>(length);
        require(extent == 0 || size <= input_.size() / extent, "GPX array dimensions overflow");
        size *= extent;
        shape.push_back(extent);
    }
    require(size == bytes.size(), "GPX array dimensions do not match its bytes");
    *output = Array{dtype, std::move(shape), state[4]};
}

double Records::element(const Array& array, std::size_t index) const {
    const auto& dtype = array.dtype;
    const auto& bytes = as<Bytes>(array.storage, "array bytes").value;
    require(index < bytes.size() / dtype.width, "missing GPX array element");
    const auto raw = bits(std::string_view(bytes).substr(index * dtype.width, dtype.width),
                          dtype.endian != '>');
    if (dtype.kind == 'f') {
        if (dtype.width == 8) return std::bit_cast<double>(raw);
        return static_cast<double>(std::bit_cast<float>(static_cast<std::uint32_t>(raw)));
    }
    if (dtype.kind == 'u' || dtype.kind == 'b') return static_cast<double>(raw);
    const auto shift = (8 - dtype.width) * 8;
    return static_cast<double>(std::bit_cast<std::int64_t>(raw << shift) >> shift);
}

double Records::number(Id id) const {
    if (const auto* integer = std::get_if<std::int64_t>(&value(id)))
        return static_cast<double>(*integer);
    if (const auto* value = std::get_if<double>(&this->value(id)); value && std::isfinite(*value))
        return *value;
    refuse("expected finite GPX number");
}

const std::string* Records::string_value(Id id) const {
    const auto& item = value(id);
    if (const auto* text = std::get_if<std::string>(&item)) return text;
    if (const auto* bytes = std::get_if<Bytes>(&item)) return &bytes->value;
    return nullptr;
}

const std::string& Records::text(Id id) const {
    if (const auto* parsed = string_value(id)) return *parsed;
    refuse("expected text in GPX");
}

bool Records::truth(Id id) const {
    const auto& item = value(id);
    if (const auto* b = std::get_if<bool>(&item)) return *b;
    if (const auto* n = std::get_if<std::int64_t>(&item)) return *n != 0;
    if (const auto* n = std::get_if<double>(&item)) return *n != 0;
    if (const auto* s = string_value(id)) return !s->empty();
    if (const auto* s = std::get_if<Sequence>(&item)) return !s->empty();
    if (const auto* d = std::get_if<Dictionary>(&item)) return !d->pairs.empty();
    return !none(id);
}

std::optional<Id> Records::find(Id id, std::string_view key) const {
    const auto& pairs = dictionary(id).pairs;
    for (std::size_t i = pairs.size(); i != 0; i -= 2) {
        const auto* name = string_value(pairs[i - 2]);
        if (name && *name == key) return pairs[i - 1];
    }
    return std::nullopt;
}

Id Records::field(Id id, std::string_view key) const {
    const auto member = find(id, key);
    if (!member) refuse("missing GPX field " + std::string(key));
    return *member;
}

Sequence Records::read() {
    Sequence records;
    while (offset_ < input_.size()) {
        switch (byte()) {
            case '.':
                require(stack_.size() == 1 && records.size() < 64, "invalid GPX record boundary");
                records.push_back(pop());
                memo_.clear();
                break;
            case '(':
                push(marker);
                break;
            case ')':
            case ']':
                add(Sequence{});
                break;
            case '}':
                add(Dictionary{});
                break;
            case 't':
                add(marked());
                break;
            case 0x85: {
                const Id a = pop();
                add(Sequence{a});
                break;
            }
            case 0x86: {
                const Id b = pop(), a = pop();
                add(Sequence{a, b});
                break;
            }
            case 0x87: {
                const Id c = pop(), b = pop(), a = pop();
                add(Sequence{a, b, c});
                break;
            }
            case 'N':
                add(std::monostate{});
                break;
            case 0x88:
                add(true);
                break;
            case 0x89:
                add(false);
                break;
            case 'I':
            case 'L':
                add(decimal(line()));
                break;
            case 'K':
                add(static_cast<std::int64_t>(byte()));
                break;
            case 'M':
                add(static_cast<std::int64_t>(little(2)));
                break;
            case 'J':
                add(static_cast<std::int64_t>(std::bit_cast<std::int32_t>(little(4))));
                break;
            case 0x8a: {
                const auto size = byte();
                require(size <= 8, "GPX integer is too wide");
                const auto data = take(size);
                std::uint64_t n = bits(data, true);
                if (size != 0 && size < 8 && (static_cast<std::uint8_t>(data.back()) & 128U) != 0)
                    n |= std::numeric_limits<std::uint64_t>::max() << (size * 8U);
                add(std::bit_cast<std::int64_t>(n));
                break;
            }
            case 'G':
                add(std::bit_cast<double>(bits(take(8), false)));
                break;
            case 'X':
                add(std::string(take(little(4))));
                break;
            case 'T':
                add(Bytes{std::string(take(little(4)))});
                break;
            case 'U':
                add(Bytes{std::string(take(byte()))});
                break;
            case 'q':
                set_memo(byte());
                break;
            case 'r':
                set_memo(little(4));
                break;
            case 'h':
                get_memo(byte());
                break;
            case 'j':
                get_memo(little(4));
                break;
            case 'e':
                extend(marked(), false);
                break;
            case 'a':
                extend({pop()}, false);
                break;
            case 'u':
                extend(marked(), true);
                break;
            case 's': {
                const Id v = pop(), k = pop();
                extend({k, v}, true);
                break;
            }
            case 'c':
                read_global();
                break;
            case 'R':
                reduce();
                break;
            case 'b':
                build();
                break;
            case 0x80:
                require(byte() == 2, "unsupported GPX pickle protocol");
                break;
            default:
                refuse("unsupported GPX record opcode");
        }
    }
    require(stack_.empty() && !records.empty(), "incomplete GPX project");
    return records;
}
}  // namespace edi::gpx
